"""Comparação lado a lado de dois parlamentares."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Autoria, Parlamentar, Proposicao
from app.services import ranking, temas, votos

LIMITE_COAUTORIAS = 20
LIMITE_TEMAS = 12


def _pessoa(p: Parlamentar) -> dict:
    return {
        "id": p.id,
        "casa": p.casa,
        "nome_parlamentar": p.nome_parlamentar,
        "partido": p.partido,
        "uf": p.uf,
        "foto_url": p.foto_url,
    }


def _temas_lado_a_lado(session: Session, a: Parlamentar, b: Parlamentar) -> list[dict]:
    """Projetos como autor principal por tema, para os dois, nos temas em que algum dos
    dois mais apresentou."""
    por_tema: dict[str, dict] = {}
    for lado, p in (("a", a), ("b", b)):
        for t in temas.projetos_por_tema(session, p)["temas"]:
            linha = por_tema.setdefault(t["tema"], {"tema": t["tema"], "a": 0, "b": 0})
            linha[lado] = t["primeiro_autor"]
    linhas = [t for t in por_tema.values() if t["a"] or t["b"]]
    linhas.sort(key=lambda t: (-(t["a"] + t["b"]), t["tema"]))
    return linhas[:LIMITE_TEMAS]


def _coautorias(session: Session, a: Parlamentar, b: Parlamentar) -> dict:
    """Projetos em que os dois aparecem como autores (principal ou coautor)."""
    aa, ab = aliased(Autoria), aliased(Autoria)
    base = (
        select(Proposicao)
        .join(aa, and_(aa.proposicao_id == Proposicao.id, aa.parlamentar_id == a.id))
        .join(ab, and_(ab.proposicao_id == Proposicao.id, ab.parlamentar_id == b.id))
    )
    total = session.scalar(select(func.count()).select_from(base.subquery()))
    itens = session.scalars(
        base.order_by(Proposicao.data_apresentacao.desc()).limit(LIMITE_COAUTORIAS)
    ).all()
    return {
        "total": total or 0,
        "itens": [
            {
                "sigla_tipo": p.sigla_tipo,
                "numero": p.numero,
                "ano": p.ano,
                "ementa": p.ementa,
                "data_apresentacao": p.data_apresentacao,
                "situacao": p.situacao,
                "virou_lei": p.virou_lei,
                "url": p.url,
            }
            for p in itens
        ],
    }


def comparar(session: Session, a: Parlamentar, b: Parlamentar, ano: int) -> dict:
    lista = ranking.listar(session, ano=ano)
    mesma_casa = a.casa == b.casa
    return {
        "ano": ano,
        "anos_disponiveis": lista["anos_disponiveis"],
        "a": _pessoa(a),
        "b": _pessoa(b),
        "numeros_a": ranking.resumo_de(session, a, ano),
        "numeros_b": ranking.resumo_de(session, b, ano),
        "criterios": lista["criterios"],
        "medias": lista["medias"],
        "mesma_casa": mesma_casa,
        "temas": _temas_lado_a_lado(session, a, b),
        "convergencia": votos.convergencia(session, a, b, ano) if mesma_casa else None,
        "coautorias": _coautorias(session, a, b),
        "atualizado_em": lista["atualizado_em"],
    }
