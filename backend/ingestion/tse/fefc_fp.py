"""Distribuição do FEFC e do Fundo Partidário por gênero e por cor ou raça (TSE).

O zip de cada eleição (2020, 2022, 2024) traz quatro CSVs: `fefc_genero`, `fefc_cor_raca`,
`fp_genero` e `fp_cor_raca`. Os de FEFC são pequenos (uma linha por partido e categoria); os
de Fundo Partidário têm uma linha por diretório (180 mil em 2024), então são somados por
partido e esfera na leitura. Só ficam as somas.

Armadilha: `VR_PARTIDO_FEFC` é o total do partido e se repete em cada linha dele (uma por
gênero, ou por gênero e cor). Somar a coluna conta o valor duas ou quatro vezes; por isso
`partido_fefc_fp.valor_partido` avisa para tomar um valor por partido.
"""

import argparse
import csv
import io
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PartidoFefcFp
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_fefc_fp"
URL = f"{comum_tse.BASE}/fefc_fp/fefc_fp_{{ano}}.zip"


def _ler(payload: Any, nome: str) -> list[dict[str, str]]:
    with comum_tse.abrir_zip(payload) as z:
        with z.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
            return list(csv.DictReader(texto, delimiter=";"))


def _inteiro(texto: str | None) -> int:
    try:
        return int((texto or "0").strip())
    except ValueError:
        return 0


def _cor(texto: str | None) -> str:
    """'NÃO NEGRA' -> 'Não negra'."""
    return comum.limpar_categoria(comum_tse.texto(texto) or "")


def fefc(linhas: list[dict[str, str]], ano: int, com_cor: bool) -> list[dict[str, Any]]:
    """Uma linha por partido e categoria; já vem agregado do TSE."""
    return [
        {
            "ano": ano, "fundo": "FEFC", "partido": linha["SG_PARTIDO"].strip(),
            "esfera": "Nacional", "genero": linha["DS_GENERO"].strip(),
            "cor_raca": _cor(linha.get("DS_COR_RACA")) if com_cor else "",
            "candidatos": _inteiro(linha.get("QT_CANDIDATO")),
            "valor_recebido": comum_tse.valor(linha.get("VR_TOTAL_RECEBIDO_FEFC")),
            "valor_minimo_cota": comum_tse.valor(linha.get("VR_REPASSE_MINIMO_COTA")),
            "valor_partido": comum_tse.valor(linha.get("VR_PARTIDO_FEFC")),
        }
        for linha in linhas
    ]  # fmt: skip


def fundo_partidario(linhas: list[dict[str, str]], ano: int, com_cor: bool) -> list[dict[str, Any]]:
    """Soma os diretórios (um por linha) por partido, esfera, gênero e, se for o caso, cor."""
    somas: dict[tuple, list] = defaultdict(lambda: [0, Decimal(0)])
    for linha in linhas:
        chave = (
            linha["SG_PARTIDO"].strip(), linha["DS_ESFERA_PARTIDARIA"].strip(),
            linha["DS_GENERO"].strip(), _cor(linha.get("DS_COR_RACA")) if com_cor else "",
        )  # fmt: skip
        somas[chave][0] += _inteiro(linha.get("QT_CANDIDATO"))
        somas[chave][1] += comum_tse.valor(linha.get("VR_TOTAL_RECEBIDO_FP"))
    return [
        {
            "ano": ano, "fundo": "FP", "partido": partido, "esfera": esfera, "genero": genero,
            "cor_raca": cor, "candidatos": candidatos, "valor_recebido": valor,
            "valor_minimo_cota": None, "valor_partido": None,
        }
        for (partido, esfera, genero, cor), (candidatos, valor) in somas.items()
    ]  # fmt: skip


def resumir(payload: Any, ano: int) -> list[dict[str, Any]]:
    return [
        *fefc(_ler(payload, f"fefc_genero_{ano}.csv"), ano, com_cor=False),
        *fefc(_ler(payload, f"fefc_cor_raca_{ano}.csv"), ano, com_cor=True),
        *fundo_partidario(_ler(payload, f"fp_genero_{ano}.csv"), ano, com_cor=False),
        *fundo_partidario(_ler(payload, f"fp_cor_raca_{ano}.csv"), ano, com_cor=True),
    ]


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        linhas = resumir(payload, ano)
        if not linhas:
            raise RuntimeError(f"Nenhuma linha de FEFC/FP em {ano}: nada alterado.")
        session.execute(delete(PartidoFefcFp).where(PartidoFefcFp.ano == ano))
        session.execute(insert(PartidoFefcFp), linhas)
        return len(linhas)

    try:
        return comum.executar_ingestao(
            FONTE, URL.format(ano=ano), baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
        )
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code != 404:
            raise
        print(f"  {FONTE}: o TSE ainda não publicou a eleição de {ano}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="+", default=[2024])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um só ano)")
    args = parser.parse_args()
    for ano_ in args.ano:
        print(f"{FONTE} {ano_}: {executar(ano_, de_raw=args.de_raw)} linhas")
