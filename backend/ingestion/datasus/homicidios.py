"""Homicídios por município de residência no SIM (Sistema de Informações sobre Mortalidade) do
DATASUS, o mesmo dado que o Atlas da Violência (Ipea) usa.

Homicídio = causa básica (CID-10) de X85 a Y09 (agressões) ou Y35 e Y36 (intervenção legal e
operações de guerra), o recorte do Atlas. Só os anos fechados (`CID10/DORES`, um DBC por UF de
residência e ano), lidos por `ingestion.datasus.dbc`: só duas colunas, `CODMUNRES` (6 dígitos,
sem o dígito verificador) e `CAUSABAS`. Nada além das contagens é guardado: nenhum dado de pessoa
sai do arquivo.
"""

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, HomicidioSim, Municipio
from app.services.pib import CODIGO_UF
from ingestion import comum
from ingestion.datasus import dbc

FONTE = "datasus_homicidios"
PASTA = "SIM/CID10/DORES/"
URL = dbc.FTP + PASTA
ANO_INICIAL = 2014
ARQUIVO = re.compile(r"^DO([A-Z]{2})(\d{4})\.dbc$", re.IGNORECASE)
COLUNAS = ("CODMUNRES", "CAUSABAS")


def e_homicidio(causa: str) -> bool:
    g = causa[:3].upper()
    return "X85" <= g <= "Y09" or g in ("Y35", "Y36")


def contar(regs) -> tuple[Counter, int]:
    """Homicídios por município (6 dígitos) e o total dos registros."""
    por_mun: Counter = Counter()
    total = 0
    for r in regs:
        if e_homicidio(r["CAUSABAS"]):
            total += 1
            por_mun[r["CODMUNRES"]] += 1
    return por_mun, total


def ler_dbf(caminho: Path) -> tuple[Counter, int]:
    """Conta homicídios por município (6 dígitos) num DBF do SIM e o total do arquivo."""
    return contar(dbc.registros(caminho, COLUNAS))


def listar() -> list[tuple[str, int, str]]:
    arquivos = [
        (m.group(1).upper(), int(m.group(2)), m.group(0))
        for m in dbc.listar(PASTA, ARQUIVO)
        if m.group(1).upper() != "BR" and int(m.group(2)) >= ANO_INICIAL
    ]
    return sorted(arquivos, key=lambda a: (a[1], a[0]))


def baixar(client: httpx.Client) -> dict[str, Any]:
    recorte: dict[str, Any] = {"anos": {}}
    for uf, ano, nome in listar():
        por_mun, total = contar(dbc.ler_remoto(PASTA, nome, COLUNAS))
        do_ano = recorte["anos"].setdefault(str(ano), {"uf": {}, "municipios": {}})
        do_ano["uf"][uf] = total
        for cod, n in por_mun.items():
            do_ano["municipios"][cod] = do_ano["municipios"].get(cod, 0) + n
    return recorte


def normalizar(recorte: dict[str, Any], mapa6: dict[str, str]) -> list[dict[str, Any]]:
    """Contagens -> linhas (código de 7 dígitos, 2 da UF ou 1 do Brasil). Municípios só com o
    código "ignorado" (ex.: 420000) entram no estado, não numa cidade."""
    linhas = []
    for ano_txt, do_ano in recorte["anos"].items():
        ano = int(ano_txt)
        if len(do_ano["uf"]) < 27:
            continue  # ano incompleto (algum estado ainda sem arquivo): fora
        for uf, n in do_ano["uf"].items():
            if uf in CODIGO_UF:
                linhas.append({"codigo": CODIGO_UF[uf], "ano": ano, "homicidios": n})
        linhas.append({"codigo": "1", "ano": ano, "homicidios": sum(do_ano["uf"].values())})
        com_ocorrencia = {}
        for cod6, n in do_ano["municipios"].items():
            ibge = mapa6.get(cod6[:6])
            if ibge:
                com_ocorrencia[ibge] = com_ocorrencia.get(ibge, 0) + n
        # Cidade sem nenhum homicídio no ano entra com zero (o arquivo só traz quem morreu).
        for ibge in mapa6.values():
            linhas.append({"codigo": ibge, "ano": ano, "homicidios": com_ocorrencia.get(ibge, 0)})
    return linhas


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    mapa6 = {ibge[:6]: ibge for ibge in session.scalars(select(Municipio.ibge))}
    linhas = normalizar(payload, mapa6)
    if len({r["ano"] for r in linhas}) < 1 or len(linhas) < 5000:
        raise ValueError("SIM sem nenhum ano completo; abortando.")
    session.execute(delete(HomicidioSim))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(HomicidioSim), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} linhas (lugar × ano)")
