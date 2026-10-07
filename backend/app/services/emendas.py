"""Emendas individuais recebidas por um município."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmendaPagamento, FonteIngestao, Municipio, Parlamentar
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE_NOME = "Emendas parlamentares por favorecido (Portal da Transparência, CGU)"
FONTE_URL = "https://portaldatransparencia.gov.br/emendas"


def resumo_municipio(session: Session, municipio: Municipio, limite_outros: int = 10) -> dict:
    do_municipio = EmendaPagamento.municipio_ibge == municipio.ibge

    por_grupo = dict(
        session.execute(
            select(EmendaPagamento.grupo, func.sum(EmendaPagamento.valor))
            .where(do_municipio)
            .group_by(EmendaPagamento.grupo)
        ).all()
    )
    por_ano = session.execute(
        select(EmendaPagamento.ano_emenda, func.sum(EmendaPagamento.valor))
        .where(do_municipio)
        .group_by(EmendaPagamento.ano_emenda)
        .order_by(EmendaPagamento.ano_emenda)
    ).all()

    total = func.sum(EmendaPagamento.valor).label("total")
    # Parlamentares em exercício (com vínculo): todos, para marcar os cards.
    com_vinculo = session.execute(
        select(Parlamentar, total)
        .join(EmendaPagamento, EmendaPagamento.parlamentar_id == Parlamentar.id)
        .where(do_municipio)
        .group_by(Parlamentar.id)
        .order_by(total.desc())
    ).all()
    # Autores sem vínculo (ex-parlamentares ou nome não identificado): os maiores.
    sem_vinculo = session.execute(
        select(EmendaPagamento.autor_nome, total)
        .where(do_municipio, EmendaPagamento.parlamentar_id.is_(None))
        .group_by(EmendaPagamento.autor_nome)
        .order_by(total.desc())
        .limit(limite_outros)
    ).all()
    n_autores = session.scalar(
        select(func.count(func.distinct(EmendaPagamento.autor_codigo))).where(do_municipio)
    )

    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "transparencia_emendas", FonteIngestao.status == "ok"
        )
    )
    return {
        "municipio": {"ibge": municipio.ibge, "nome": municipio.nome, "uf": municipio.uf},
        "desde": INICIO_LEGISLATURA.year,
        "total": sum(por_grupo.values(), start=0),
        "total_prefeitura": por_grupo.get("prefeitura", 0),
        "total_entidades": por_grupo.get("entidade", 0),
        "por_ano": [{"ano": a, "total": t} for a, t in por_ano],
        "parlamentares": [
            {"parlamentar": p, "total": t, "do_estado": p.uf == municipio.uf}
            for p, t in com_vinculo
        ],
        "outros_autores": [{"autor_nome": n, "total": t} for n, t in sem_vinculo],
        "numero_autores": n_autores or 0,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }
