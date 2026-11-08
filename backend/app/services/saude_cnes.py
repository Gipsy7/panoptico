"""Saúde de um município no CNES (DATASUS), no mês mais recente: leitos de internação por mil
moradores e quantos são do SUS, leitos complementares (UTI e intermediários) por 100 mil, unidades
básicas por 10 mil e hospitais, com o estado e o Brasil contados do mesmo jeito. A população é a do
IBGE do mesmo ano ou a última anterior."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PopulacaoIbge, SaudeCnes
from app.services.pib import CODIGO_UF

FONTE = "datasus_cnes"
FONTE_NOME = "Ministério da Saúde, DATASUS (Cadastro Nacional de Estabelecimentos de Saúde, CNES)"
FONTE_URL = "https://cnes.datasus.gov.br/"


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _lugar(session: Session, codigo: str) -> dict | None:
    r = session.get(SaudeCnes, codigo)
    if r is None:
        return None
    pop = session.scalar(
        select(PopulacaoIbge.valor)
        .where(PopulacaoIbge.codigo == codigo, PopulacaoIbge.ano <= r.ano)
        .order_by(PopulacaoIbge.ano.desc())
        .limit(1)
    )

    def por(n: int, base: int) -> float | None:
        return base * n / pop if pop else None

    return {
        "leitos": r.leitos,
        "leitos_sus": r.leitos_sus,
        "leitos_por_mil": por(r.leitos, 1000),
        "leitos_complementares": r.leitos_complementares,
        "leitos_complementares_sus": r.leitos_complementares_sus,
        "complementares_por_100_mil": por(r.leitos_complementares, 100_000),
        "ubs": r.ubs,
        "ubs_por_10_mil": por(r.ubs, 10_000),
        "hospitais": r.hospitais,
    }


def do_lugar(session: Session, codigo: str, uf: str, comparar_estado: bool = True) -> dict:
    r = session.get(SaudeCnes, codigo)
    return {
        "municipio_ibge": codigo,
        "uf": uf,
        "ano": r.ano if r else None,
        "mes": r.mes if r else None,
        "cidade": _lugar(session, codigo),
        "estado": _lugar(session, CODIGO_UF.get(uf, "")) if comparar_estado else None,
        "brasil": _lugar(session, "1"),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
