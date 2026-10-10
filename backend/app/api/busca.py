from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import BuscaResposta
from app.services import busca

router = APIRouter()


@router.get("/busca", response_model=BuscaResposta)
def buscar(
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[
        str | None, Query(min_length=1, max_length=100, description="Parte do nome")
    ] = None,
    nome: Annotated[
        str | None, Query(min_length=1, max_length=100, description="Igual a q")
    ] = None,
) -> dict:
    """Busca por nome: pessoas de todos os níveis (Congresso, Executivo, assembleias e câmaras),
    partidos e pessoas de eleições passadas. Cada grupo tem limite próprio."""
    termo = q or nome
    if not termo:
        raise HTTPException(422, "Informe o termo em q.")
    return busca.buscar(session, termo)
