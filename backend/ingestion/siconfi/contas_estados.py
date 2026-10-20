"""Contas anuais dos estados e do DF no SICONFI (Tesouro Nacional), Declaração de Contas Anuais.

Mesma API e mesmo recorte de `contas.py` (receita realizada, despesa paga e despesa paga por
função de governo), só que o ente é a UF (`id_ente` = código IBGE de 2 dígitos): 27 consultas
por anexo e ano. A despesa paga é a "exceto intraorçamentárias", como nos municípios. Os dados
são anuais (entregues até abril do ano seguinte): a carga roda uma vez por mês.
"""

import argparse
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import ContasEstado, FonteIngestao
from ingestion import comum
from ingestion.siconfi.contas import URL, _consultar, recortar

FONTE = "siconfi_contas_estados"
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip


def baixar(client: httpx.Client, ano: int) -> list[dict]:
    resultados = []
    falhas = []
    for codigo in UF_POR_CODIGO:
        receitas = _consultar(client, codigo, ano, "DCA-Anexo I-C")
        despesas = _consultar(client, codigo, ano, "DCA-Anexo I-E")
        if receitas is None or despesas is None:
            falhas.append(codigo)  # falha da API não pode virar "sem despesa"
            continue
        if recorte := recortar(codigo, receitas, despesas):
            resultados.append(recorte)
    if falhas:
        print(f"  {ano}: consulta falhou para {[UF_POR_CODIGO[c] for c in falhas]}", flush=True)
    return resultados


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, payload: list[dict], ingestao: FonteIngestao) -> int:
        if len(payload) < len(UF_POR_CODIGO) // 2:  # API fora do ar ou ano não entregue
            raise ValueError(f"Só {len(payload)} estados com contas de {ano}; abortando.")
        session.execute(delete(ContasEstado).where(ContasEstado.ano == ano))
        linhas = [
            {
                "uf": UF_POR_CODIGO[c["ibge"]],
                "ano": ano,
                "populacao": c["populacao"],
                "receita_total": Decimal(str(c["receita_total"]))
                if c["receita_total"] is not None
                else None,
                "despesa_paga": Decimal(str(c["despesa_paga"]))
                if c["despesa_paga"] is not None
                else None,
                "despesa_por_area": c["despesa_por_area"],
            }
            for c in payload
        ]
        session.execute(insert(ContasEstado), linhas)
        return len(linhas)

    return comum.executar_ingestao(
        FONTE, URL, lambda client: baixar(client, ano), carregar, de_raw=de_raw,
        prefixo_raw=f"{ano}_",
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", help="Padrão: os dois últimos anos fechados")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    anos = args.ano or [a - 1 for a in comum.anos_padrao()]
    for ano in anos:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} estados")
