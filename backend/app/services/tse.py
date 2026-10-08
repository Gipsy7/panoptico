"""Dados do TSE de um parlamentar: candidaturas, bens declarados e campanha."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BemDeclarado, CampanhaResumo, Candidatura, FonteIngestao, Parlamentar

FONTE_NOME = "Tribunal Superior Eleitoral (dados abertos)"
FONTE_URL = "https://dadosabertos.tse.jus.br/"
URL_CANDIDATOS = "https://dadosabertos.tse.jus.br/dataset/candidatos-{ano}"
URL_CONTAS = "https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-{ano}"

# Cargos que dão o mandato atual em cada Casa (suplentes assumem no lugar do titular).
CARGOS_DO_MANDATO = {
    "camara": {"DEPUTADO FEDERAL"},
    "senado": {"SENADOR", "1º SUPLENTE", "2º SUPLENTE"},
}
ITENS_DE_BENS = 30


def _candidatura(c: Candidatura) -> dict:
    return {
        "ano": c.ano_eleicao,
        "cargo": c.cargo.capitalize(),
        "unidade": c.unidade,
        "partido": c.partido,
        "numero": c.numero,
        "situacao": (c.situacao_turno or "").capitalize() or None,
    }


def _total_bens(session: Session, candidatura_id: int) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(BemDeclarado.valor), 0)).where(
            BemDeclarado.candidatura_id == candidatura_id
        )
    )


def resumo(session: Session, parlamentar: Parlamentar) -> dict:
    candidaturas = session.scalars(
        select(Candidatura)
        .where(Candidatura.parlamentar_id == parlamentar.id)
        .order_by(Candidatura.ano_eleicao.desc())
    ).all()
    com_bens = [
        c
        for c in candidaturas
        if session.scalar(select(func.count()).where(BemDeclarado.candidatura_id == c.id))
    ]

    bens = None
    if com_bens:
        atual = com_bens[0]
        itens = session.scalars(
            select(BemDeclarado)
            .where(BemDeclarado.candidatura_id == atual.id)
            .order_by(BemDeclarado.valor.desc())
        ).all()
        anterior = com_bens[1] if len(com_bens) > 1 else None
        bens = {
            "candidatura": _candidatura(atual),
            "total": _total_bens(session, atual.id),
            "quantidade": len(itens),
            "itens": [
                {"tipo": b.tipo, "descricao": b.descricao, "valor": b.valor}
                for b in itens[:ITENS_DE_BENS]
            ],
            "anterior": (
                {"candidatura": _candidatura(anterior), "total": _total_bens(session, anterior.id)}
                if anterior
                else None
            ),
            "fonte_url": URL_CANDIDATOS.format(ano=atual.ano_eleicao),
        }

    # A campanha que deu o mandato atual: a candidatura mais recente ao cargo da Casa.
    do_mandato = next(
        (c for c in candidaturas if c.cargo in CARGOS_DO_MANDATO[parlamentar.casa]), None
    )
    campanha = None
    if do_mandato is not None:
        contas = session.get(CampanhaResumo, do_mandato.id)
        if contas is not None:
            campanha = {
                "candidatura": _candidatura(do_mandato),
                "receitas_total": contas.receitas_total,
                "receitas_por_origem": [
                    {"nome": k, "valor": v} for k, v in contas.receitas_por_origem.items()
                ],
                "despesas_total": contas.despesas_total,
                "despesas_por_tipo": [
                    {"nome": k, "valor": v} for k, v in contas.despesas_por_tipo.items()
                ],
                "numero_doadores": contas.numero_doadores,
                "fonte_url": URL_CONTAS.format(ano=do_mandato.ano_eleicao),
            }

    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(["tse_candidaturas", "tse_bens", "tse_campanha"]),
            FonteIngestao.status == "ok",
        )
    )
    return {
        "candidaturas": [_candidatura(c) for c in candidaturas],
        "bens": bens,
        "campanha": campanha,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }
