"""Resumo dos projetos de lei de um parlamentar na legislatura atual."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Autoria, FonteIngestao, Parlamentar, Proposicao
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

NOMES_TIPO = {
    "PL": "Projetos de lei",
    "PLP": "Projetos de lei complementar",
    "PEC": "Propostas de emenda à Constituição",
    "PDL": "Projetos de decreto legislativo",
}

FONTES = {
    "camara": {
        "fontes": ("camara_autores",),
        "nome": "Proposições legislativas (Dados Abertos da Câmara)",
        "url": "https://dadosabertos.camara.leg.br/",
    },
    "senado": {
        "fontes": ("senado_proposicoes",),
        "nome": "Processos legislativos (Dados Abertos do Senado)",
        "url": "https://legis.senado.leg.br/dadosabertos/docs/",
    },
}


def media_primeiro_autor(session: Session, casa: str) -> Decimal:
    """Média de projetos como primeiro autor por parlamentar em exercício (zeros incluídos)."""
    contagens = (
        select(func.count(Autoria.proposicao_id).label("n"))
        .select_from(Parlamentar)
        .outerjoin(
            Autoria,
            (Autoria.parlamentar_id == Parlamentar.id) & Autoria.primeiro_autor.is_(True),
        )
        .where(Parlamentar.casa == casa, Parlamentar.em_exercicio.is_(True))
        .group_by(Parlamentar.id)
        .subquery()
    )
    return session.scalar(select(func.coalesce(func.avg(contagens.c.n), 0))).quantize(
        Decimal("0.1")
    )


def resumo(session: Session, parlamentar: Parlamentar, limite: int = 10) -> dict:
    do_parlamentar = Autoria.parlamentar_id == parlamentar.id
    base = select(Proposicao, Autoria.primeiro_autor).join(
        Autoria, Autoria.proposicao_id == Proposicao.id
    )

    por_tipo = session.execute(
        select(
            Proposicao.sigla_tipo,
            func.count().label("total"),
            func.count().filter(Autoria.primeiro_autor).label("primeiro_autor"),
            func.count().filter(Autoria.primeiro_autor & Proposicao.virou_lei).label("normas"),
        )
        .join(Autoria, Autoria.proposicao_id == Proposicao.id)
        .where(do_parlamentar)
        .group_by(Proposicao.sigla_tipo)
    ).all()
    por_tipo = sorted(por_tipo, key=lambda t: list(NOMES_TIPO).index(t.sigla_tipo))

    recentes = session.execute(
        base.where(do_parlamentar, Autoria.primeiro_autor.is_(True))
        .order_by(Proposicao.data_apresentacao.desc(), Proposicao.numero.desc())
        .limit(limite)
    ).all()
    normas = session.execute(
        base.where(do_parlamentar, Autoria.primeiro_autor.is_(True), Proposicao.virou_lei)
        .order_by(Proposicao.data_apresentacao.desc())
        .limit(limite)
    ).all()

    fonte = FONTES[parlamentar.casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte.in_(fonte["fontes"]), FonteIngestao.status == "ok"
        )
    )

    def item(proposicao: Proposicao, primeiro: bool) -> dict:
        return {
            "sigla_tipo": proposicao.sigla_tipo,
            "numero": proposicao.numero,
            "ano": proposicao.ano,
            "ementa": proposicao.ementa,
            "data_apresentacao": proposicao.data_apresentacao,
            "situacao": proposicao.situacao,
            "virou_lei": proposicao.virou_lei,
            "url": proposicao.url,
            "primeiro_autor": primeiro,
        }

    return {
        "desde": INICIO_LEGISLATURA,
        "primeiro_autor": sum(t.primeiro_autor for t in por_tipo),
        "coautor": sum(t.total - t.primeiro_autor for t in por_tipo),
        "viraram_norma": sum(t.normas for t in por_tipo),
        "media_casa_primeiro_autor": media_primeiro_autor(session, parlamentar.casa),
        "por_tipo": [
            {
                "sigla": t.sigla_tipo,
                "nome": NOMES_TIPO[t.sigla_tipo],
                "primeiro_autor": t.primeiro_autor,
                "coautor": t.total - t.primeiro_autor,
            }
            for t in por_tipo
        ],
        "recentes": [item(p, a) for p, a in recentes],
        "viraram_norma_lista": [item(p, a) for p, a in normas],
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }
