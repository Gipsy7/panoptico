"""PIB de um município (IBGE), com o PIB por morador do estado e do Brasil no mesmo ano.

O PIB vem a preços correntes (valores da época, sem descontar a inflação): a comparação útil é
com o estado e o Brasil no mesmo ano, não a soma ao longo do tempo. O PIB por morador só existe
nos anos com população do IBGE no mesmo ano (`populacao_ibge`; 2023 não tem estimativa)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PibIbge, PopulacaoIbge

FONTE = "ibge_pib"
FONTE_NOME = "IBGE (PIB dos Municípios, tabela 5938 do SIDRA)"
FONTE_URL = "https://sidra.ibge.gov.br/tabela/5938"
CODIGO_UF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip
SETORES = [
    ("vab_agropecuaria", "Agropecuária"),
    ("vab_industria", "Indústria"),
    ("vab_servicos", "Comércio e serviços"),
    ("vab_administracao", "Administração pública, educação e saúde públicas"),
]


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _por_habitante(pib_mil: Decimal, populacao: int | None) -> float | None:
    return float(pib_mil * 1000 / populacao) if populacao else None


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    codigos = [ibge, CODIGO_UF.get(uf, ""), "1"]
    pibs = session.scalars(select(PibIbge).where(PibIbge.codigo.in_(codigos))).all()
    pops = {
        (p.codigo, p.ano): p.valor
        for p in session.scalars(select(PopulacaoIbge).where(PopulacaoIbge.codigo.in_(codigos)))
    }
    por = {(p.codigo, p.ano): p for p in pibs}
    serie = []
    for p in sorted((p for p in pibs if p.codigo == ibge), key=lambda p: p.ano):
        uf_p, br_p = por.get((codigos[1], p.ano)), por.get(("1", p.ano))
        serie.append(
            {
                "ano": p.ano,
                "pib": float(p.pib) * 1000,
                "por_habitante": _por_habitante(p.pib, pops.get((ibge, p.ano))),
                "uf_por_habitante": _por_habitante(uf_p.pib, pops.get((codigos[1], p.ano)))
                if uf_p
                else None,
                "brasil_por_habitante": _por_habitante(br_p.pib, pops.get(("1", p.ano)))
                if br_p
                else None,
            }
        )
    com_setores = max(
        (p for p in pibs if p.codigo == ibge and p.vab_total), key=lambda p: p.ano, default=None
    )
    setores = None
    if com_setores:
        setores = {
            "ano": com_setores.ano,
            "itens": [
                {
                    "setor": nome,
                    "valor": float(getattr(com_setores, campo) or 0) * 1000,
                    "percentual": float(
                        100 * (getattr(com_setores, campo) or 0) / com_setores.vab_total
                    ),
                }
                for campo, nome in SETORES
            ],
        }
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "serie": serie,
        "setores": setores,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
