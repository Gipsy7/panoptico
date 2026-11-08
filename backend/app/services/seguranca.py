"""Homicídios de moradores de um município (SIM/DATASUS), ano a ano, com a taxa por 100 mil
moradores (população do IBGE do mesmo ano ou a última anterior) e, por ser mais estável em
cidades pequenas, a taxa média dos últimos 3 anos. Estado e Brasil contados do mesmo jeito."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, HomicidioSim, PopulacaoIbge
from app.services.pib import CODIGO_UF

FONTE = "datasus_homicidios"
FONTE_NOME = "Ministério da Saúde, DATASUS (Sistema de Informações sobre Mortalidade, SIM)"
FONTE_URL = "https://datasus.saude.gov.br/mortalidade-desde-1996-pela-cid-10"
ANOS_MEDIA = 3


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _populacoes(session: Session, codigo: str) -> list[tuple[int, int]]:
    return list(
        session.execute(
            select(PopulacaoIbge.ano, PopulacaoIbge.valor)
            .where(PopulacaoIbge.codigo == codigo)
            .order_by(PopulacaoIbge.ano)
        ).all()
    )


def _pop(pops: list[tuple[int, int]], ano: int) -> int | None:
    validas = [v for a, v in pops if a <= ano]
    return validas[-1] if validas else None


def _lugar(session: Session, codigo: str) -> dict:
    serie = list(
        session.execute(
            select(HomicidioSim.ano, HomicidioSim.homicidios)
            .where(HomicidioSim.codigo == codigo)
            .order_by(HomicidioSim.ano)
        ).all()
    )
    pops = _populacoes(session, codigo)
    pontos = []
    for ano, n in serie:
        pop = _pop(pops, ano)
        pontos.append({"ano": ano, "homicidios": n, "por_100_mil": 1e5 * n / pop if pop else None})
    ultimos = pontos[-ANOS_MEDIA:]
    pops_ult = [_pop(pops, p["ano"]) for p in ultimos]
    media = None
    if len(ultimos) == ANOS_MEDIA and all(pops_ult):
        media = 1e5 * sum(p["homicidios"] for p in ultimos) / sum(pops_ult)
    return {"serie": pontos, "media_3_anos_por_100_mil": media}


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    cidade = _lugar(session, ibge)
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "cidade": cidade,
        "estado": _lugar(session, CODIGO_UF.get(uf, "")),
        "brasil": _lugar(session, "1"),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
