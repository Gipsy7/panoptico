"""Projetos de um parlamentar por tema oficial (classificação da Câmara)."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Autoria, Parlamentar, Proposicao, ProposicaoTema
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO, TEMA_HOMENAGENS


def projetos_por_tema(session: Session, parlamentar: Parlamentar) -> dict:
    """Uma proposição pode ter mais de um tema, então a soma por tema passa do total.
    Cada casa tem a sua classificação oficial (rótulos diferentes)."""
    linhas = session.execute(
        select(
            ProposicaoTema.tema,
            func.count().filter(Autoria.primeiro_autor),
            func.count().filter(~Autoria.primeiro_autor),
        )
        .select_from(Autoria)
        .join(Proposicao, Proposicao.id == Autoria.proposicao_id)
        .join(
            ProposicaoTema,
            and_(
                ProposicaoTema.casa == Proposicao.casa,
                ProposicaoTema.proposicao_id_externo == Proposicao.id_externo,
            ),
        )
        .where(Autoria.parlamentar_id == parlamentar.id, ProposicaoTema.tema != SEM_CLASSIFICACAO)
        .group_by(ProposicaoTema.tema)
    ).all()
    temas = sorted(
        ({"tema": t, "primeiro_autor": p, "coautor": c} for t, p, c in linhas),
        key=lambda x: (-x["primeiro_autor"], -x["coautor"], x["tema"]),
    )
    homenagens = next((t["primeiro_autor"] for t in temas if t["tema"] == TEMA_HOMENAGENS), 0)
    return {"disponivel": True, "temas": temas, "homenagens": homenagens}
