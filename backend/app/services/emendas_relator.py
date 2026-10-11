"""Indicações de emendas de relator-geral (RP9) feitas por um parlamentar, segundo a planilha
oficial da Comissão Mista de Orçamento (LOA 2022). Só descreve o que está registrado."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmendaRelatorIndicacao, FonteIngestao, Parlamentar
from ingestion.congresso.emendas_relator import FONTE, URL, URL_PAGINA

FONTE_NOME = "Indicações de beneficiários de emendas RP9, LOA 2022 (Comissão Mista de Orçamento)"
LIMITE = 100


def resumo(session: Session, parlamentar: Parlamentar) -> dict | None:
    base = EmendaRelatorIndicacao.parlamentar_id == parlamentar.id
    totais = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(EmendaRelatorIndicacao.valor_solicitado), 0),
            func.count(func.distinct(EmendaRelatorIndicacao.beneficiario)),
        ).where(base)
    ).one()
    if not totais[0]:
        return None
    orgao = func.coalesce(EmendaRelatorIndicacao.orgao, "Órgão não informado")
    por_orgao = session.execute(
        select(
            orgao,
            func.count(),
            func.sum(EmendaRelatorIndicacao.valor_solicitado),
        )
        .where(base)
        .group_by(orgao)
        .order_by(func.sum(EmendaRelatorIndicacao.valor_solicitado).desc())
    ).all()
    itens = session.scalars(
        select(EmendaRelatorIndicacao)
        .where(base)
        .order_by(EmendaRelatorIndicacao.valor_solicitado.desc(), EmendaRelatorIndicacao.id)
        .limit(LIMITE)
    ).all()
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status.in_(("ok", "sem_mudanca"))
        )
    )
    return {
        "ano": itens[0].ano,
        "quantidade": totais[0],
        "valor_solicitado": totais[1],
        "beneficiarios": totais[2],
        "por_orgao": [{"orgao": o, "quantidade": n, "valor": v} for o, n, v in por_orgao],
        "itens": [
            {
                "numero": i.numero,
                "data_cadastro": i.data_cadastro,
                "beneficiario": i.beneficiario,
                "uf": i.uf,
                "orgao": i.orgao,
                "objeto": i.objeto,
                "valor_solicitado": i.valor_solicitado,
            }
            for i in itens
        ],
        "limite": LIMITE,
        "fonte_nome": FONTE_NOME,
        "fonte_url": URL_PAGINA,
        "arquivo_url": URL,
        "atualizado_em": atualizado_em,
    }
