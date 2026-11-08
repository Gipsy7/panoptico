"""Trabalho formal de um município (IBGE, Cadastro Central de Empresas): empresas, pessoas
ocupadas, assalariados e salário médio por ano, com o salário médio do estado e do Brasil no mesmo
ano, e onde as pessoas trabalham (seções da CNAE; só municípios com 50 mil habitantes ou mais).
Não inclui o trabalho informal."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmpregoIbge, EmpregoSetor, FonteIngestao
from app.services.pib import CODIGO_UF

FONTE = "ibge_cempre"
FONTE_NOME = "IBGE (Cadastro Central de Empresas, tabelas 9509 e 9510 do SIDRA)"
FONTE_URL = "https://sidra.ibge.gov.br/tabela/9509"
SETORES = 8


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _num(v) -> float | None:
    return float(v) if v is not None else None


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    codigos = [ibge, CODIGO_UF.get(uf, ""), "1"]
    linhas = session.scalars(select(EmpregoIbge).where(EmpregoIbge.codigo.in_(codigos))).all()
    por = {(r.codigo, r.ano): r for r in linhas}
    serie = []
    for r in sorted((r for r in linhas if r.codigo == ibge), key=lambda r: r.ano):
        uf_r, br_r = por.get((codigos[1], r.ano)), por.get(("1", r.ano))
        serie.append(
            {
                "ano": r.ano,
                "empresas": _num(r.empresas),
                "pessoal_ocupado": _num(r.pessoal_ocupado),
                "assalariados": _num(r.assalariados),
                "salario_medio": _num(r.salario_medio),
                "salario_medio_sm": _num(r.salario_medio_sm),
                "uf_salario_medio": _num(uf_r.salario_medio) if uf_r else None,
                "brasil_salario_medio": _num(br_r.salario_medio) if br_r else None,
            }
        )
    setores = session.scalars(
        select(EmpregoSetor)
        .where(EmpregoSetor.codigo == ibge)
        .order_by(EmpregoSetor.pessoal_ocupado.desc())
    ).all()
    total = sum(s.pessoal_ocupado for s in setores)
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "serie": serie,
        "setores_ano": setores[0].ano if setores else None,
        "setores": [
            {
                "secao": s.secao,
                "nome": s.nome,
                "pessoal_ocupado": float(s.pessoal_ocupado),
                "percentual": float(100 * s.pessoal_ocupado / total) if total else None,
            }
            for s in setores[:SETORES]
        ],
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
