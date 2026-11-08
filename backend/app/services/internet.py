"""Internet fixa de um município (Anatel): acessos de banda larga fixa no mês mais recente, por
100 moradores (população do IBGE do mesmo ano ou o último anterior), com o estado e o Brasil
somados do mesmo jeito, e a parte de fibra e de mais de 34 Mbps."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, InternetFixa, Municipio, PopulacaoIbge
from app.services.pib import CODIGO_UF

FONTE = "anatel_banda_larga"
FONTE_NOME = "Anatel (dados abertos de acessos de banda larga fixa)"
FONTE_URL = "https://www.gov.br/anatel/pt-br/dados/acessos/banda-larga-fixa"


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _populacao(session: Session, codigo: str, ano: int) -> int | None:
    return session.scalar(
        select(PopulacaoIbge.valor)
        .where(PopulacaoIbge.codigo == codigo, PopulacaoIbge.ano <= ano)
        .order_by(PopulacaoIbge.ano.desc())
        .limit(1)
    )


def _por_100(acessos: int | None, pop: int | None) -> float | None:
    return 100 * acessos / pop if acessos is not None and pop else None


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    r = session.get(InternetFixa, ibge)
    if r is None:
        return {"municipio_ibge": ibge, "uf": uf, "ano": None, "mes": None, "acessos": None,
                "por_100_moradores": None, "uf_por_100_moradores": None,
                "brasil_por_100_moradores": None, "percentual_fibra": None,
                "percentual_rapida": None, "fonte_nome": FONTE_NOME, "fonte_url": FONTE_URL,
                "atualizado_em": atualizado_em(session)}  # fmt: skip
    acessos_uf = session.scalar(
        select(func.sum(InternetFixa.acessos))
        .join(Municipio, Municipio.ibge == InternetFixa.codigo)
        .where(Municipio.uf == uf)
    )
    acessos_br = session.scalar(select(func.sum(InternetFixa.acessos)))
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "ano": r.ano,
        "mes": r.mes,
        "acessos": r.acessos,
        "por_100_moradores": _por_100(r.acessos, _populacao(session, ibge, r.ano)),
        "uf_por_100_moradores": _por_100(
            acessos_uf, _populacao(session, CODIGO_UF.get(uf, ""), r.ano)
        ),
        "brasil_por_100_moradores": _por_100(acessos_br, _populacao(session, "1", r.ano)),
        "percentual_fibra": 100 * r.acessos_fibra / r.acessos if r.acessos else None,
        "percentual_rapida": 100 * r.acessos_rapidos / r.acessos if r.acessos else None,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
