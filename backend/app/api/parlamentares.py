from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Parlamentar
from app.schemas import GastosResposta, ParlamentarDetalhe
from app.services import gastos

router = APIRouter()


def _buscar(session: Session, parlamentar_id: int) -> Parlamentar:
    encontrado = session.get(Parlamentar, parlamentar_id)
    if encontrado is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    return encontrado


@router.get("/parlamentares/{parlamentar_id}", response_model=ParlamentarDetalhe)
def parlamentar(
    parlamentar_id: int, session: Annotated[Session, Depends(get_session)]
) -> Parlamentar:
    return _buscar(session, parlamentar_id)


@router.get("/parlamentares/{parlamentar_id}/gastos", response_model=GastosResposta)
def gastos_do_parlamentar(
    parlamentar_id: int,
    session: Annotated[Session, Depends(get_session)],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente com dados")] = None,
) -> dict:
    p = _buscar(session, parlamentar_id)
    anos = gastos.anos_disponiveis(session, p)
    if not anos:
        raise HTTPException(404, "Ainda não há gastos carregados para esta Casa.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem gastos carregados para {ano}.")
    return gastos.resumo(session, p, ano)
