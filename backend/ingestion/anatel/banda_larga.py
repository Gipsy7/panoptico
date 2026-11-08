"""Banda larga fixa por município (Anatel, dados abertos de acessos), no mês mais recente.

Arquivo: `https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip`
(~1 GB). Dentro, um CSV por ano (`Acessos_Banda_Larga_Fixa_<ano>.csv`, `;`, UTF-8 com BOM) com
uma linha por mês, empresa, município, faixa de velocidade, tecnologia e tipo de pessoa. Somamos
os acessos do último mês por município (código IBGE), e quantos são de fibra (FTTH/FTTB) e de
mais de 34 Mbps.

Armadilha: o `Densidade_Banda_Larga_Fixa.csv` do mesmo zip mistura unidades (o Brasil aparece
com 22,3 em dez/2022, 94,0 em dez/2025 e 27,2 em set/2026: ora por 100 habitantes, ora por 100
domicílios). Não é usado: a API divide os acessos pela população do IBGE no mesmo ano.

O bruto guardado é o recorte (a soma por município); o zip continua na Anatel.
"""

import argparse
import csv
import io
import re
import zipfile
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, InternetFixa
from ingestion import comum

FONTE = "anatel_banda_larga"
URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip"
FIBRA = {"FTTH", "FTTB"}
RAPIDA = "> 34Mbps"


def somar(linhas) -> dict[str, Any]:
    """Linhas do CSV -> soma do último mês por município: {ibge: [acessos, fibra, rápidos]}."""
    por_mes: dict[tuple[int, int], dict[str, list[int]]] = {}
    for r in linhas:
        ibge = (r.get("Código IBGE Município") or "").strip()
        if not re.fullmatch(r"\d{7}", ibge):
            continue
        try:
            acessos = int(r["Acessos"])
            chave = (int(r["Ano"]), int(r["Mês"]))
        except (KeyError, ValueError):
            continue
        s = por_mes.setdefault(chave, {}).setdefault(ibge, [0, 0, 0])
        s[0] += acessos
        if (r.get("Tecnologia") or "").strip().upper() in FIBRA:
            s[1] += acessos
        if (r.get("Faixa de Velocidade") or "").strip() == RAPIDA:
            s[2] += acessos
    if not por_mes:
        return {"ano": None, "mes": None, "municipios": {}}
    ano, mes = max(por_mes)
    return {"ano": ano, "mes": mes, "municipios": por_mes[(ano, mes)]}


def ler_zip(caminho: Path) -> dict[str, Any]:
    with zipfile.ZipFile(caminho) as z:
        anuais = [
            n for n in z.namelist() if re.fullmatch(r"Acessos_Banda_Larga_Fixa_\d{4}\.csv", n)
        ]
        if not anuais:
            raise ValueError("Zip da Anatel sem o CSV anual de acessos.")
        nome = max(anuais)
        with z.open(nome) as f:
            texto = io.TextIOWrapper(f, encoding="utf-8-sig", newline="")
            return somar(csv.DictReader(texto, delimiter=";"))


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    municipios = payload["municipios"]
    if len(municipios) < 5000:
        raise ValueError(f"Banda larga com só {len(municipios)} municípios; abortando.")
    session.execute(delete(InternetFixa))
    linhas = [
        {"codigo": ibge, "ano": payload["ano"], "mes": payload["mes"], "acessos": v[0],
         "acessos_fibra": v[1], "acessos_rapidos": v[2], "ingestao_id": ingestao.id}
        for ibge, v in municipios.items()
    ]  # fmt: skip
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(InternetFixa), linhas[inicio : inicio + 5000])
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> dict[str, Any]:
        caminho = comum.baixar_para_arquivo(client, URL)
        try:
            return ler_zip(caminho)
        finally:
            caminho.unlink(missing_ok=True)

    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa o recorte guardado, sem baixar")
    parser.add_argument("--zip", type=Path, help="Lê um zip da Anatel já baixado (sem gravar)")
    args = parser.parse_args()
    if args.zip:
        r = ler_zip(args.zip)
        print(f"{r['ano']}/{r['mes']}: {len(r['municipios'])} municípios")
    else:
        print(f"{FONTE}: {executar(de_raw=args.de_raw)} municípios")
