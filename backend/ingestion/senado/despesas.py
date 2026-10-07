"""Gastos da cota parlamentar (CEAPS) dos senadores, API administrativa do Senado."""

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum

FONTE = "senado_despesas"
CASA = "senado"
URL = "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"


def normalizar(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id_externo_parlamentar": str(d["codSenador"]),
            "mes": int(d["mes"]),
            "categoria": comum.limpar_categoria(d.get("tipoDespesa")),
            "fornecedor": (d.get("fornecedor") or "").strip() or None,
            "cnpj_cpf": d.get("cpfCnpj") or None,
            "valor": Decimal(str(d.get("valorReembolsado") or 0)),
            "data": date.fromisoformat(d["data"][:10]) if d.get("data") else None,
            "url_documento": None,  # o Senado não publica o comprovante por despesa
            "id_externo": str(d["id"]),
        }
        for d in payload
    ]


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> list[dict[str, Any]]:
        return comum.get_json(client, URL.format(ano=ano))

    def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
        linhas = comum.vincular_parlamentares(session, CASA, normalizar(payload))
        return comum.recarregar_despesas(session, CASA, ano, linhas, ingestao)

    return comum.executar_ingestao(
        FONTE, URL.format(ano=ano), baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=comum.anos_padrao())
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} registros")
