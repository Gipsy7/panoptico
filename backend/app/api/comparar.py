from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Parlamentar
from app.schemas import ComparacaoResposta
from app.services import comparar, ranking

router = APIRouter()


@router.get("/comparar", response_model=ComparacaoResposta)
def comparar_parlamentares(
    session: Annotated[Session, Depends(get_session)],
    a: Annotated[int, Query(description="Id do primeiro parlamentar")],
    b: Annotated[int, Query(description="Id do segundo parlamentar")],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente")] = None,
) -> dict:
    if a == b:
        raise HTTPException(422, "Escolha dois parlamentares diferentes.")
    pa, pb = session.get(Parlamentar, a), session.get(Parlamentar, b)
    if pa is None or pb is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    anos = ranking.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Os números ainda não foram calculados.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem números para {ano}.")
    return comparar.comparar(session, pa, pb, ano)
