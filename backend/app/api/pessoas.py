"""Pessoa pública (a mesma em todas as fontes) e a linha do tempo dela."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import CasoResposta, CasoResumo, LinhaDoTempo, PessoaResposta
from app.services import pessoas

router = APIRouter()


@router.get("/pessoas/{pessoa_id}", response_model=PessoaResposta)
def pessoa(pessoa_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """A pessoa e os perfis dela no site (mandato federal, na câmara ou assembleia, e
    candidaturas), só os ligados por chave forte ou revisados."""
    resultado = pessoas.pessoa(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/eventos", response_model=LinhaDoTempo)
def eventos(
    pessoa_id: int,
    session: Annotated[Session, Depends(get_session)],
    tipo: Annotated[str | None, Query(max_length=40)] = None,
    de: date | None = None,
    ate: date | None = None,
) -> dict:
    """Linha do tempo da pessoa, com a fonte oficial de cada fato."""
    resultado = pessoas.eventos(session, pessoa_id, tipo, de, ate)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/casos", response_model=list[CasoResumo])
def lista_de_casos(session: Annotated[Session, Depends(get_session)]) -> list[dict]:
    """Casos montados com documentos oficiais (só os revisados; rascunhos não entram)."""
    return pessoas.casos(session)


@router.get("/casos/{slug}", response_model=CasoResposta)
def caso(slug: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Documentos oficiais do caso e o papel de cada pessoa segundo eles."""
    resultado = pessoas.caso(session, slug)
    if resultado is None:
        raise HTTPException(404, "Caso não encontrado.")
    return resultado
