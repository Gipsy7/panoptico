"""Dados do TSE: candidaturas, bens declarados e campanha.

Servem dois públicos: o perfil dos parlamentares federais (todas as candidaturas ligadas
pelo CPF) e os eleitos para câmaras municipais e assembleias, que só existem no TSE.
"""

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
CARGOS_ESTADUAIS = ("DEPUTADO ESTADUAL", "DEPUTADO DISTRITAL")
ITENS_DE_BENS = 30
SITUACOES = {
    "ELEITO POR QP": "Eleito pelo quociente partidário",
    "ELEITO POR MÉDIA": "Eleito pela média (sobra de vagas)",
}


def _situacao(texto: str | None) -> str | None:
    if not texto:
        return None
    return SITUACOES.get(texto, texto.capitalize())


def _candidatura(c: Candidatura) -> dict:
    return {
        "ano": c.ano_eleicao,
        "cargo": c.cargo.capitalize(),
        "unidade": c.unidade,
        "partido": c.partido,
        "numero": c.numero,
        "situacao": _situacao(c.situacao_turno),
    }


def _total_bens(session: Session, candidatura_id: int) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(BemDeclarado.valor), 0)).where(
            BemDeclarado.candidatura_id == candidatura_id
        )
    )


def _tem_bens(session: Session, candidatura_id: int) -> bool:
    return bool(
        session.scalar(select(func.count()).where(BemDeclarado.candidatura_id == candidatura_id))
    )


def _bens(session: Session, atual: Candidatura, anterior: Candidatura | None) -> dict:
    itens = session.scalars(
        select(BemDeclarado)
        .where(BemDeclarado.candidatura_id == atual.id)
        .order_by(BemDeclarado.valor.desc())
    ).all()
    return {
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


def _campanha(session: Session, c: Candidatura) -> dict | None:
    contas = session.get(CampanhaResumo, c.id)
    if contas is None:
        return None
    return {
        "candidatura": _candidatura(c),
        "receitas_total": contas.receitas_total,
        "receitas_por_origem": [
            {"nome": k, "valor": v} for k, v in contas.receitas_por_origem.items()
        ],
        "despesas_total": contas.despesas_total,
        "despesas_por_tipo": [{"nome": k, "valor": v} for k, v in contas.despesas_por_tipo.items()],
        "numero_doadores": contas.numero_doadores,
        "fonte_url": URL_CONTAS.format(ano=c.ano_eleicao),
    }


def _atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(["tse_candidaturas", "tse_bens", "tse_campanha"]),
            FonteIngestao.status == "ok",
        )
    )


def resumo(session: Session, parlamentar: Parlamentar) -> dict:
    """Perfil do parlamentar federal: bens da candidatura mais recente (comparados com a
    anterior) e a campanha que deu o mandato atual."""
    candidaturas = session.scalars(
        select(Candidatura)
        .where(Candidatura.parlamentar_id == parlamentar.id)
        .order_by(Candidatura.ano_eleicao.desc())
    ).all()
    com_bens = [c for c in candidaturas if _tem_bens(session, c.id)]
    do_mandato = next(
        (c for c in candidaturas if c.cargo in CARGOS_DO_MANDATO[parlamentar.casa]), None
    )
    return {
        "candidaturas": [_candidatura(c) for c in candidaturas],
        "bens": _bens(session, com_bens[0], com_bens[1] if len(com_bens) > 1 else None)
        if com_bens
        else None,
        "campanha": _campanha(session, do_mandato) if do_mandato else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }


def _eleito(c: Candidatura) -> dict:
    return {
        "id": c.id,
        "nome_urna": c.nome_urna,
        "partido": c.partido,
        "numero": c.numero,
        "situacao": _situacao(c.situacao_turno),
        "uf": c.uf,
        "parlamentar_id": c.parlamentar_id,
    }


def _lista(session: Session, *condicoes) -> list[dict]:
    eleitos = session.scalars(
        select(Candidatura)
        .where(*condicoes, Candidatura.situacao_turno.like("ELEITO%"))
        .order_by(Candidatura.nome_urna)
    ).all()
    return [_eleito(c) for c in eleitos]


def vereadores(session: Session, municipio_ibge: str) -> dict:
    itens = _lista(
        session, Candidatura.cargo == "VEREADOR", Candidatura.municipio_ibge == municipio_ibge
    )
    ano = max(
        session.scalars(
            select(Candidatura.ano_eleicao).where(Candidatura.municipio_ibge == municipio_ibge)
        ).all(),
        default=None,
    )
    return {
        "ano_eleicao": ano,
        "itens": itens,
        "fonte_nome": FONTE_NOME,
        "fonte_url": URL_CANDIDATOS.format(ano=ano or 2024),
        "atualizado_em": _atualizado_em(session),
    }


def deputados_estaduais(session: Session, uf: str) -> dict:
    itens = _lista(session, Candidatura.cargo.in_(CARGOS_ESTADUAIS), Candidatura.uf == uf.upper())
    return {
        "ano_eleicao": 2022,
        "itens": itens,
        "fonte_nome": FONTE_NOME,
        "fonte_url": URL_CANDIDATOS.format(ano=2022),
        "atualizado_em": _atualizado_em(session),
    }


def eleito(session: Session, candidatura: Candidatura) -> dict:
    """Perfil de um eleito que só existe no TSE (vereador, deputado estadual)."""
    return {
        **_eleito(candidatura),
        "cargo": candidatura.cargo.capitalize(),
        "unidade": candidatura.unidade,
        "municipio_ibge": candidatura.municipio_ibge,
        "ano_eleicao": candidatura.ano_eleicao,
        "bens": _bens(session, candidatura, None) if _tem_bens(session, candidatura.id) else None,
        "campanha": _campanha(session, candidatura),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": _atualizado_em(session),
    }
