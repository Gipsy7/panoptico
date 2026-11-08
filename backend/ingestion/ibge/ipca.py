"""IPCA (IBGE, SIDRA tabela 1737, variável 2266): número-índice mensal, base dez/1993 = 100,
desde jan/2000. Serve para mostrar valores de anos diferentes "em reais de hoje": o fator de um ano
é a média do índice no ano mais recente completo dividida pela média do índice no ano do valor."""

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, IpcaIndice
from ingestion import comum

FONTE = "ibge_ipca"
URL = "https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/200001-209912/variaveis/2266"


def baixar(client: httpx.Client) -> Any:
    return comum.get_json(client, URL, {"localidades": "N1[all]"})


def normalizar(payload: Any) -> list[dict]:
    serie = payload[0]["resultados"][0]["series"][0]["serie"]
    linhas = []
    for periodo, texto in serie.items():
        texto = (texto or "").strip()
        if not texto or texto in {"...", "-", "X"}:
            continue
        linhas.append({"ano": int(periodo[:4]), "mes": int(periodo[4:]), "indice": Decimal(texto)})
    return linhas


def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    if len(linhas) < 200:
        raise ValueError("IPCA com menos de 200 meses; abortando.")
    session.execute(delete(IpcaIndice))
    session.execute(insert(IpcaIndice), [{**r, "ingestao_id": ingestao.id} for r in linhas])
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} meses")
