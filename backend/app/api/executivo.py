"""Executivo com conteúdo: contas do estado, painel e agenda de presidente, governador,
prefeito e vices (docs/DECISOES.md, 19/10/2026)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.executivo import AgendaResposta, ContasEstadoResposta, PainelExecutivo
from app.services import contas, executivo
from app.services.representantes import UFS

router = APIRouter()

TipoAgenda = Literal["reuniao", "evento", "audiencia", "audiencia_publica", "viagem", "presente"]


@router.get("/estados/{uf}/contas", response_model=ContasEstadoResposta)
def contas_do_estado(
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Contas anuais do governo do estado no SICONFI: receita, despesa por área, por habitante
    e a média dos estados (com quantos ficaram fora por falta de dado)."""
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    resultado = contas.resumo_estado(session, uf.upper())
    if resultado is None:
        raise HTTPException(404, "Sem contas entregues ao Tesouro para este estado.")
    return resultado


@router.get("/executivo/{candidatura_id}/painel", response_model=PainelExecutivo)
def painel_do_executivo(
    candidatura_id: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    """Em qual ente o cargo existe (União, estado ou município) e os números-resumo desse
    ente, cada um com a fonte e a data; o que não existe vem com o motivo."""
    candidatura = executivo.candidatura_executivo(session, candidatura_id)
    if candidatura is None:
        raise HTTPException(404, "Candidatura do Executivo não encontrada.")
    return executivo.painel(session, candidatura)


@router.get("/executivo/{candidatura_id}/agenda", response_model=AgendaResposta)
def agenda_do_executivo(
    candidatura_id: int,
    session: Annotated[Session, Depends(get_session)],
    tipo: TipoAgenda | None = None,
    ano: Annotated[int | None, Query(ge=2022, le=2100)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    """Agenda do e-Agendas (CGU) de quem foi agente público federal (ex.: vice-presidente
    como ministro), 30 por página, do mais recente para o mais antigo."""
    candidatura = executivo.candidatura_executivo(session, candidatura_id)
    if candidatura is None:
        raise HTTPException(404, "Candidatura do Executivo não encontrada.")
    return executivo.agenda(session, candidatura, tipo, ano, pagina)
