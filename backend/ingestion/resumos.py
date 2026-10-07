"""Recalcula a tabela resumo_parlamentar a partir dos dados já carregados.

Roda como última etapa do run_all. Não baixa nada (não há bruto): só consolida, para
que a lista ordenável e o comparador respondam rápido. Uso:
    uv run python -m ingestion.resumos
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, delete, exists, func, insert, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Autoria,
    Despesa,
    EmendaPagamento,
    FonteIngestao,
    Parlamentar,
    Proposicao,
    ProposicaoTema,
    ResumoParlamentar,
)
from app.services import presenca, votos
from ingestion import comum
from ingestion.proposicoes_comum import TEMA_HOMENAGENS

FONTE = "resumos"


def _projetos(session: Session) -> dict[int, dict[str, int]]:
    """Projetos como autor principal: sem homenagens, só homenagens e que viraram norma."""
    homenagem = exists().where(
        and_(
            ProposicaoTema.casa == Proposicao.casa,
            ProposicaoTema.proposicao_id_externo == Proposicao.id_externo,
            ProposicaoTema.tema == TEMA_HOMENAGENS,
        )
    )
    linhas = session.execute(
        select(
            Autoria.parlamentar_id,
            func.count().filter(~homenagem),
            func.count().filter(homenagem),
            func.count().filter(Proposicao.virou_lei),
        )
        .join(Proposicao, Proposicao.id == Autoria.proposicao_id)
        .where(Autoria.primeiro_autor.is_(True))
        .group_by(Autoria.parlamentar_id)
    )
    return {
        pid: {"projetos": projetos, "homenagens": homenagens, "normas": normas}
        for pid, projetos, homenagens, normas in linhas
    }


def calcular(session: Session, anos: list[int]) -> list[dict]:
    parlamentares = session.execute(
        select(Parlamentar.id, Parlamentar.casa).where(Parlamentar.em_exercicio)
    ).all()
    projetos = _projetos(session)
    emendas = dict(
        session.execute(
            select(EmendaPagamento.parlamentar_id, func.sum(EmendaPagamento.valor))
            .where(EmendaPagamento.parlamentar_id.is_not(None))
            .group_by(EmendaPagamento.parlamentar_id)
        ).all()
    )

    linhas = []
    for ano in anos:
        gastos = dict(
            session.execute(
                select(Despesa.parlamentar_id, func.sum(Despesa.valor))
                .where(Despesa.ano == ano)
                .group_by(Despesa.parlamentar_id)
            ).all()
        )
        presencas, alinhamentos = {}, {}
        for casa in ("camara", "senado"):
            for pid, votacoes, contagem in session.execute(
                presenca._CONTAGENS, {"ano": ano, "casa": casa, "parlamentar_id": -1}
            ):
                presencas[pid] = presenca._resumir(casa, votacoes, contagem)
            alinhamentos.update(votos.alinhamentos(session, casa, ano))

        for pid, _casa in parlamentares:
            p = presencas.get(pid, {"votou": 0, "total_votacoes": 0})
            a = alinhamentos.get(pid)
            proj = projetos.get(pid, {"projetos": 0, "homenagens": 0, "normas": 0})
            linhas.append(
                {
                    "parlamentar_id": pid,
                    "ano": ano,
                    "gastos": gastos.get(pid, Decimal(0)),
                    "presenca_votou": p["votou"],
                    "presenca_total": p["total_votacoes"],
                    "governo_iguais": a["governo"].iguais if a else 0,
                    "governo_total": a["governo"].total if a else 0,
                    "partido_iguais": a["partido"].iguais if a else 0,
                    "partido_total": a["partido"].total if a else 0,
                    **proj,
                    "emendas_pagas": emendas.get(pid, Decimal(0)),
                }
            )
    return linhas


def executar(anos: list[int] | None = None) -> int:
    anos = anos or comum.anos_padrao()
    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=FONTE, url="interno", arquivo_raw="-")
        session.add(ingestao)
        session.flush()
        linhas = calcular(session, anos)
        if not linhas:
            raise ValueError("Nenhum parlamentar em exercício; abortando o resumo.")
        session.execute(delete(ResumoParlamentar))
        session.execute(insert(ResumoParlamentar), linhas)
        ingestao.registros = len(linhas)
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now(UTC)
        session.commit()
    return len(linhas)


if __name__ == "__main__":
    print(f"{FONTE}: {executar()} linhas")
