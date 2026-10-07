"""Resumo dos gastos da cota parlamentar de um parlamentar num ano."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Despesa, FonteIngestao, Parlamentar

FONTES = {
    "camara": {
        "fonte": "camara_despesas",
        "nome": "Cota para o Exercício da Atividade Parlamentar (CEAP)",
        "url": "https://www.camara.leg.br/transparencia/gastos-parlamentares",
    },
    "senado": {
        "fonte": "senado_despesas",
        "nome": "Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS)",
        "url": "https://www25.senado.leg.br/web/transparencia/sen/",
    },
}


def anos_disponiveis(session: Session, parlamentar: Parlamentar) -> list[int]:
    return list(
        session.scalars(
            select(Despesa.ano)
            .where(Despesa.casa == parlamentar.casa)
            .distinct()
            .order_by(Despesa.ano.desc())
        )
    )


def media_da_casa(session: Session, casa: str, ano: int) -> Decimal:
    """Média do total gasto por parlamentar em exercício (quem não gastou entra com zero)."""
    totais = (
        select(func.coalesce(func.sum(Despesa.valor), 0).label("total"))
        .select_from(Parlamentar)
        .outerjoin(Despesa, (Despesa.parlamentar_id == Parlamentar.id) & (Despesa.ano == ano))
        .where(Parlamentar.casa == casa, Parlamentar.em_exercicio.is_(True))
        .group_by(Parlamentar.id)
        .subquery()
    )
    return session.scalar(select(func.coalesce(func.avg(totais.c.total), 0))).quantize(
        Decimal("0.01")
    )


def resumo(session: Session, parlamentar: Parlamentar, ano: int) -> dict:
    do_parlamentar = (Despesa.parlamentar_id == parlamentar.id, Despesa.ano == ano)

    total = session.scalar(select(func.coalesce(func.sum(Despesa.valor), 0)).where(*do_parlamentar))
    por_categoria = session.execute(
        select(Despesa.categoria, func.sum(Despesa.valor).label("total"))
        .where(*do_parlamentar)
        .group_by(Despesa.categoria)
        .order_by(func.sum(Despesa.valor).desc())
    ).all()
    por_mes = session.execute(
        select(Despesa.mes, func.sum(Despesa.valor).label("total"))
        .where(*do_parlamentar)
        .group_by(Despesa.mes)
        .order_by(Despesa.mes)
    ).all()
    maiores = session.scalars(
        select(Despesa).where(*do_parlamentar).order_by(Despesa.valor.desc()).limit(10)
    ).all()
    ultimo_mes = session.scalar(
        select(func.max(Despesa.mes)).where(Despesa.casa == parlamentar.casa, Despesa.ano == ano)
    )

    fonte = FONTES[parlamentar.casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )

    return {
        "ano": ano,
        "anos_disponiveis": anos_disponiveis(session, parlamentar),
        "ultimo_mes": ultimo_mes,
        "total": total,
        "media_casa": media_da_casa(session, parlamentar.casa, ano),
        "por_categoria": [{"categoria": c, "total": t} for c, t in por_categoria],
        "por_mes": [{"mes": m, "total": t} for m, t in por_mes],
        "maiores_despesas": maiores,
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }
