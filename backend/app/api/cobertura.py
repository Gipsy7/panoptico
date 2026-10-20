from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.cobertura import CoberturaResposta
from app.services import cobertura

router = APIRouter()


@router.get("/cobertura", response_model=CoberturaResposta)
def cobertura_por_uf(uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None) -> dict:
    """O que o site mostra e o que falta, por casa e seção, igual para todos os estados."""
    resposta = cobertura.cobertura(uf)
    if resposta is None:
        raise HTTPException(404, "Estado não encontrado.")
    return resposta
