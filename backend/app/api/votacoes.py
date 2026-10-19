from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.votacao import VotacaoDetalhe
from app.services import votacao_detalhe

router = APIRouter()


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
