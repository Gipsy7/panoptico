from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import BuscaResposta
from app.services import busca

router = APIRouter()


@router.get("/busca", response_model=BuscaResposta)
def buscar(
    nome: Annotated[str, Query(min_length=1, max_length=100, description="Parte do nome")],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Pessoas de todos os níveis com esse nome: Congresso, Executivo, assembleias e câmaras."""
    return {"itens": busca.buscar(session, nome)}
