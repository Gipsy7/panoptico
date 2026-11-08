"""Saúde por município no CNES (Cadastro Nacional de Estabelecimentos de Saúde) do DATASUS, na
competência (mês) mais recente com as 27 UFs publicadas:

- leitos (arquivo LT, um registro por estabelecimento e tipo de leito): os de internação existentes
  e os do SUS (TP_LEITO 1, 2, 4, 5, 6 e 7, como no TabNet) e, à parte, os complementares
  (TP_LEITO 3: UTI e unidades intermediárias), também com os do SUS;
- unidades (arquivo ST, um registro por estabelecimento): unidades básicas (TP_UNID 01, posto de
  saúde, e 02, centro de saúde/UBS) e hospitais (05 geral, 07 especializado e 15 unidade mista).

Só as contagens por município (`CODUFMUN`, 6 dígitos) são guardadas; nenhum CPF, CNPJ ou nome.
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Municipio, SaudeCnes
from app.services.pib import CODIGO_UF
from ingestion import comum
from ingestion.datasus import dbc

FONTE = "datasus_cnes"
PASTA = "CNES/200508_/Dados/"
URL = dbc.FTP + PASTA
CAMPOS = ("leitos", "leitos_sus", "leitos_complementares", "leitos_complementares_sus", "ubs",
          "hospitais")  # fmt: skip
UBS = {"01", "02"}
HOSPITAIS = {"05", "07", "15"}
COMPLEMENTAR = "3"


def _arquivo(tipo: str) -> re.Pattern:
    return re.compile(rf"^{tipo}([A-Z]{{2}})(\d{{4}})\.dbc$", re.IGNORECASE)


def competencia_mais_recente() -> str:
    """O AAMM mais recente com LT e ST das 27 UFs."""
    por_aamm: dict[str, set] = defaultdict(set)
    for tipo in ("LT", "ST"):
        for m in dbc.listar(f"{PASTA}{tipo}/", _arquivo(tipo)):
            por_aamm[m.group(2)].add((tipo, m.group(1).upper()))
    completas = [a for a, s in por_aamm.items() if len(s) >= 2 * len(CODIGO_UF)]
    if not completas:
        raise ValueError("CNES sem nenhuma competência completa.")
    return max(completas)


def contar_leitos(regs, mun: dict) -> None:
    """Bruto: por município, [existentes, SUS] de cada tipo de leito (TP_LEITO)."""
    for r in regs:
        tipos = mun.setdefault(r["CODUFMUN"], {"leitos": {}, "unidades": {}})["leitos"]
        par = tipos.setdefault(r["TP_LEITO"], [0, 0])
        par[0] += int(r["QT_EXIST"] or 0)
        par[1] += int(r["QT_SUS"] or 0)


def contar_unidades(regs, mun: dict) -> None:
    """Bruto: por município, quantos estabelecimentos de cada tipo (TP_UNID)."""
    for r in regs:
        tipos = mun.setdefault(r["CODUFMUN"], {"leitos": {}, "unidades": {}})["unidades"]
        tipos[r["TP_UNID"]] = tipos.get(r["TP_UNID"], 0) + 1


def baixar(client: httpx.Client) -> dict[str, Any]:
    aamm = competencia_mais_recente()
    recorte: dict[str, Any] = {"competencia": "20" + aamm, "ufs": {}}
    colunas_lt = ("CODUFMUN", "TP_LEITO", "QT_EXIST", "QT_SUS")
    for uf in CODIGO_UF:
        mun: dict[str, dict] = {}
        contar_leitos(dbc.ler_remoto(f"{PASTA}LT/", f"LT{uf}{aamm}.dbc", colunas_lt), mun)
        contar_unidades(
            dbc.ler_remoto(f"{PASTA}ST/", f"ST{uf}{aamm}.dbc", ("CODUFMUN", "TP_UNID")), mun
        )
        recorte["ufs"][uf] = mun
    return recorte


def campos_de(bruto: dict) -> dict[str, int]:
    """Contagens por tipo -> os campos guardados."""
    v = dict.fromkeys(CAMPOS, 0)
    for tipo, (existentes, sus) in bruto["leitos"].items():
        if tipo == COMPLEMENTAR:
            v["leitos_complementares"] += existentes
            v["leitos_complementares_sus"] += sus
        else:
            v["leitos"] += existentes
            v["leitos_sus"] += sus
    for tipo, n in bruto["unidades"].items():
        v["ubs"] += n if tipo in UBS else 0
        v["hospitais"] += n if tipo in HOSPITAIS else 0
    return v


def normalizar(recorte: dict[str, Any], mapa6: dict[str, str]) -> list[dict[str, Any]]:
    ano, mes = int(recorte["competencia"][:4]), int(recorte["competencia"][4:])
    brasil = dict.fromkeys(CAMPOS, 0)
    por_ibge: dict[str, dict] = {}
    linhas = []
    for uf, mun in recorte["ufs"].items():
        total = dict.fromkeys(CAMPOS, 0)
        for cod6, bruto in mun.items():
            valores = campos_de(bruto)
            ibge = mapa6.get(cod6[:6])
            alvo = por_ibge.setdefault(ibge, dict.fromkeys(CAMPOS, 0)) if ibge else None
            for c in CAMPOS:
                total[c] += valores[c]
                if alvo is not None:
                    alvo[c] += valores[c]
        for c in CAMPOS:
            brasil[c] += total[c]
        if uf in CODIGO_UF:
            linhas.append({"codigo": CODIGO_UF[uf], "ano": ano, "mes": mes, **total})
    linhas.append({"codigo": "1", "ano": ano, "mes": mes, **brasil})
    # Cidade sem nenhum estabelecimento nos arquivos entra com zero.
    for ibge in mapa6.values():
        valores = por_ibge.get(ibge, dict.fromkeys(CAMPOS, 0))
        linhas.append({"codigo": ibge, "ano": ano, "mes": mes, **valores})
    return linhas


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    if len(payload.get("ufs", {})) < len(CODIGO_UF):
        raise ValueError("CNES sem as 27 UFs; abortando.")
    mapa6 = {ibge[:6]: ibge for ibge in session.scalars(select(Municipio.ibge))}
    linhas = normalizar(payload, mapa6)
    session.execute(delete(SaudeCnes))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(SaudeCnes), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} lugares")
