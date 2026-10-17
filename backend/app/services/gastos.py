"""Resumo dos gastos da cota parlamentar de um parlamentar num ano."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Despesa, FonteIngestao, Parlamentar, ResumoParlamentar

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


# Um ano por vez, saltando pelo índice (casa, ano, mes): poucas sondagens em vez de ler as
# ~100 mil entradas da Casa para agrupar.
_ANOS_E_ULTIMO_MES = text(
    """
    with recursive anos(ano) as (
        select min(ano) from despesa where casa = :casa
        union all
        select (select min(ano) from despesa where casa = :casa and ano > anos.ano)
          from anos where anos.ano is not null
    )
    select ano, (select max(mes) from despesa where casa = :casa and ano = anos.ano)
      from anos where ano is not null order by ano desc
    """
)


def anos_e_ultimo_mes(session: Session, casa: str) -> dict[int, int]:
    """Cada ano com gasto da Casa e o último mês com gasto nele, do ano mais novo para o mais
    antigo, numa consulta só."""
    return {int(ano): int(mes) for ano, mes in session.execute(_ANOS_E_ULTIMO_MES, {"casa": casa})}


def anos_disponiveis(session: Session, parlamentar: Parlamentar) -> list[int]:
    return list(anos_e_ultimo_mes(session, parlamentar.casa))


def _media_guardada(session: Session, casa: str, ano: int) -> Decimal | None:
    """Mesma média, lida do `resumo_parlamentar` (soma de despesas por parlamentar e ano,
    gravada a cada ingestão). Só vale se todo parlamentar em exercício tem linha no ano."""
    em_exercicio = session.scalar(
        select(func.count()).where(Parlamentar.casa == casa, Parlamentar.em_exercicio.is_(True))
    )
    linhas, media = session.execute(
        select(func.count(), func.coalesce(func.avg(ResumoParlamentar.gastos), 0))
        .join(Parlamentar, Parlamentar.id == ResumoParlamentar.parlamentar_id)
        .where(
            Parlamentar.casa == casa,
            Parlamentar.em_exercicio.is_(True),
            ResumoParlamentar.ano == ano,
        )
    ).one()
    if not linhas or linhas != em_exercicio:
        return None
    return media.quantize(Decimal("0.01"))


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


def resumo(
    session: Session,
    parlamentar: Parlamentar,
    ano: int,
    anos_meses: dict[int, int] | None = None,
    usar_guardado: bool = True,
) -> dict:
    """`anos_meses` é o resultado de `anos_e_ultimo_mes`, para quem já o leu não repetir."""
    if anos_meses is None:
        anos_meses = anos_e_ultimo_mes(session, parlamentar.casa)
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
    ultimo_mes = anos_meses.get(ano)
    media_casa = _media_guardada(session, parlamentar.casa, ano) if usar_guardado else None
    if media_casa is None:
        media_casa = media_da_casa(session, parlamentar.casa, ano)

    fonte = FONTES[parlamentar.casa]
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == fonte["fonte"], FonteIngestao.status == "ok"
        )
    )

    return {
        "ano": ano,
        "anos_disponiveis": list(anos_meses),
        "ultimo_mes": ultimo_mes,
        "total": total,
        "media_casa": media_casa,
        "por_categoria": [{"categoria": c, "total": t} for c, t in por_categoria],
        "por_mes": [{"mes": m, "total": t} for m, t in por_mes],
        "maiores_despesas": maiores,
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": atualizado_em,
    }
