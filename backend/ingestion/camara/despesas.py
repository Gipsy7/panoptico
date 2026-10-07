"""Gastos da cota parlamentar (CEAP) dos deputados, arquivo anual da Câmara.

Usa o CSV e não o JSON: só o CSV traz `ideCadastro`, que é o id do deputado na API
de Dados Abertos. O `numeroDeputadoID` do JSON é outro identificador.
"""

import argparse
import csv
import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum

FONTE = "camara_despesas"
CASA = "camara"
URL = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"


def _data(texto: str) -> date | None:
    return date.fromisoformat(texto[:10]) if texto else None


def normalizar(conteudo_zip: bytes) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
        texto = z.read(z.namelist()[0]).decode("utf-8-sig")
    registros = []
    for linha in csv.DictReader(io.StringIO(texto), delimiter=";"):
        if not linha["ideCadastro"]:
            continue  # lideranças e órgãos, não deputados
        registros.append(
            {
                "id_externo_parlamentar": linha["ideCadastro"],
                "mes": int(linha["numMes"]),
                "categoria": comum.limpar_categoria(linha["txtDescricao"]),
                "fornecedor": linha["txtFornecedor"].strip() or None,
                "cnpj_cpf": linha["txtCNPJCPF"].strip() or None,
                "valor": Decimal(linha["vlrLiquido"] or "0"),
                "data": _data(linha["datEmissao"]),
                "url_documento": linha["urlDocumento"] or None,
                "id_externo": linha["ideDocumento"] or None,
            }
        )
    return registros


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL.format(ano=ano))

    def carregar(session: Session, payload: bytes, ingestao: FonteIngestao) -> int:
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
