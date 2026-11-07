from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.votacao import CalendarioVotacoes, VotacaoDetalhe
from app.services import calendario_votacoes, votacao_detalhe

router = APIRouter()


@router.get("/votacoes/calendario", response_model=CalendarioVotacoes)
def calendario(
    session: Annotated[Session, Depends(get_session)],
    casa: Literal["camara", "senado"] = "camara",
    ano: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    dia: Annotated[date | None, Query(description="Lista só as votações deste dia")] = None,
    tipo: Annotated[
        Literal["todas", "merito", "procedimento"],
        Query(description="Recorte da lista: todas, só as sobre o texto ou só as de procedimento"),
    ] = "todas",
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    """Número de votações nominais do Plenário em cada dia de um mês (padrão: o mais recente
    com votação na Casa) e a lista das votações do mês ou do dia, no recorte pedido."""
    dados = calendario_votacoes.calendario(
        session, casa, ano, mes, dia, None if tipo == "todas" else tipo, pagina
    )
    if dados is None:
        raise HTTPException(404, "Ainda não há votações carregadas para esta Casa.")
    return dados


@router.get("/votacoes/{casa}/{id_externo}", response_model=VotacaoDetalhe)
def detalhe_da_votacao(
    casa: Literal["camara", "senado"],
    id_externo: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Uma votação nominal do Plenário: o que se votava, placar, orientações e votos.
    `id_externo` é o id da fonte (Câmara "2645346-18", Senado "7104"), estável entre cargas."""
    dados = votacao_detalhe.detalhe(session, casa, id_externo)
    if dados is None:
        raise HTTPException(404, "Votação não encontrada.")
    return dados
