"""Saneamento de um município no Censo 2022 (IBGE): % dos domicílios com água da rede geral como
forma principal, com esgoto na rede (ou fossa ligada a ela) e com lixo coletado, ao lado do
estado e do Brasil, que o IBGE publica já calculados."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, SaneamentoCenso
from app.services.pib import CODIGO_UF

FONTE = "ibge_saneamento"
FONTE_NOME = "IBGE, Censo Demográfico 2022 (características dos domicílios)"
FONTE_URL = "https://sidra.ibge.gov.br/tabela/6805"
CAMPOS = ("agua_rede", "esgoto_rede", "lixo_coletado")


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _valores(r: SaneamentoCenso | None) -> dict:
    return {c: (float(getattr(r, c)) if r and getattr(r, c) is not None else None) for c in CAMPOS}


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    cidade = session.get(SaneamentoCenso, ibge)
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "ano": cidade.ano if cidade else None,
        "cidade": _valores(cidade),
        "estado": _valores(session.get(SaneamentoCenso, CODIGO_UF.get(uf, ""))),
        "brasil": _valores(session.get(SaneamentoCenso, "1")),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
