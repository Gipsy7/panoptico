"""Resumo da prestação de contas de campanha (TSE), só das candidaturas guardadas.

O arquivo oficial tem centenas de MB (1,3 GB em 2024): é baixado direto para o disco e lido
em fluxo. Guardamos só os totais, por origem da receita e por tipo de despesa. Nomes de
doadores pessoas físicas não são guardados; contamos quantos foram.
"""

import argparse
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import CampanhaResumo, Candidatura, FonteIngestao
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_campanha"
URL = f"{comum_tse.BASE}/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{{ano}}.zip"
TIPOS_DE_DESPESA_MOSTRADOS = 8

ORIGENS = {
    "Recursos de pessoas físicas": "Pessoas físicas",
    "Recursos de Financiamento Coletivo": "Pessoas físicas",
    "Doações pela Internet": "Pessoas físicas",
    "Recursos próprios": "Recursos próprios",
    "Recursos de partido político": "Partido (outros recursos)",
    "Recursos de outros candidatos": "Outros candidatos",
}


def origem_da_receita(fonte: str | None, origem: str | None) -> str:
    """Agrupa a receita pelo que importa ao leitor: dinheiro público (fundo eleitoral e
    fundo partidário) separado do resto, e o resto pela origem declarada."""
    if fonte == "FUNDO ESPECIAL":
        return "Fundo eleitoral"
    if fonte == "FUNDO PARTIDARIO":
        return "Fundo partidário"
    return ORIGENS.get(origem or "", "Outras origens")


def resumir(receitas: Any, despesas: Any, candidaturas: dict[str, int]) -> list[dict[str, Any]]:
    por_origem: dict[int, Counter] = {}
    doadores: dict[int, set[str]] = {}
    for linha in receitas:
        id_ = candidaturas.get(linha["SQ_CANDIDATO"].strip())
        if id_ is None:
            continue
        origem = origem_da_receita(
            comum_tse.texto(linha.get("DS_FONTE_RECEITA")),
            comum_tse.texto(linha.get("DS_ORIGEM_RECEITA")),
        )
        por_origem.setdefault(id_, Counter())[origem] += comum_tse.valor(linha.get("VR_RECEITA"))
        if origem == "Pessoas físicas" and (
            doador := comum_tse.texto(linha.get("NR_CPF_CNPJ_DOADOR"))
        ):
            doadores.setdefault(id_, set()).add(doador)

    por_tipo: dict[int, Counter] = {}
    for linha in despesas:
        id_ = candidaturas.get(linha["SQ_CANDIDATO"].strip())
        if id_ is None:
            continue
        tipo = comum_tse.texto(linha.get("DS_ORIGEM_DESPESA")) or "Não informado"
        por_tipo.setdefault(id_, Counter())[tipo] += comum_tse.valor(
            linha.get("VR_DESPESA_CONTRATADA")
        )

    resumos = []
    for id_ in sorted(set(por_origem) | set(por_tipo)):
        origens = por_origem.get(id_, Counter())
        tipos = por_tipo.get(id_, Counter())
        principais = dict(tipos.most_common(TIPOS_DE_DESPESA_MOSTRADOS))
        resto = sum(tipos.values(), start=Decimal(0)) - sum(principais.values(), start=Decimal(0))
        if resto > 0:
            principais["Outras despesas"] = resto
        resumos.append(
            {
                "candidatura_id": id_,
                "receitas_total": sum(origens.values(), start=Decimal(0)),
                "receitas_por_origem": {k: float(v) for k, v in origens.most_common()},
                "despesas_total": sum(tipos.values(), start=Decimal(0)),
                "despesas_por_tipo": {k: float(v) for k, v in principais.items()},
                "numero_doadores": len(doadores.get(id_, set())),
            }
        )
    return resumos


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        candidaturas = dict(
            session.execute(
                select(Candidatura.sq_candidato, Candidatura.id).where(
                    Candidatura.ano_eleicao == ano
                )
            ).all()
        )
        if not candidaturas:
            return 0
        resumos = resumir(
            comum_tse.linhas(payload, f"receitas_candidatos_{ano}_"),
            comum_tse.linhas(payload, f"despesas_contratadas_candidatos_{ano}_"),
            candidaturas,
        )
        session.execute(
            delete(CampanhaResumo).where(
                CampanhaResumo.candidatura_id.in_(
                    select(Candidatura.id).where(Candidatura.ano_eleicao == ano)
                )
            )
        )
        if resumos:
            session.execute(insert(CampanhaResumo), resumos)
        return len(resumos)

    return comum.executar_ingestao(
        FONTE, URL.format(ano=ano), baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2018, 2022])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} candidaturas com contas")
