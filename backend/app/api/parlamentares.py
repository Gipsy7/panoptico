from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Parlamentar
from app.schemas import ParlamentarDetalhe

router = APIRouter()


@router.get("/parlamentares/{parlamentar_id}", response_model=ParlamentarDetalhe)
def parlamentar(
    parlamentar_id: int, session: Annotated[Session, Depends(get_session)]
) -> Parlamentar:
    encontrado = session.get(Parlamentar, parlamentar_id)
    if encontrado is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    return encontrado
