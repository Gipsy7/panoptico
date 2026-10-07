"""Municípios do IBGE (API de localidades)."""

import argparse
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Municipio
from ingestion import comum

FONTE = "ibge_municipios"
URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado"


def normalizar(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "ibge": str(m["municipio-id"]),
            "nome": m["municipio-nome"],
            "uf": m["UF-sigla"],
            "nome_chave": comum.chave_nome(m["municipio-nome"]),
        }
        for m in payload
    ]


def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
    registros = normalizar(payload)
    if len(registros) < 5000:
        raise ValueError(f"Só {len(registros)} municípios; abortando.")
    stmt = insert(Municipio).values(registros)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["ibge"],
            set_={c: stmt.excluded[c] for c in ("nome", "uf", "nome_chave")},
        )
    )
    return len(registros)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(
        FONTE, URL, lambda client: comum.get_json(client, URL), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} municípios")
