"""Comparador do 2º turno pelo CEP: os candidatos que o eleitor encontra na urna."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.representantes import localizar
from app.db import get_session
from app.schemas.segundo_turno import AgendaSegundoTurno, SegundoTurnoResposta
from app.services import segundo_turno

router = APIRouter()


@router.get("/segundo-turno/agenda", response_model=AgendaSegundoTurno)
def agenda(session: Annotated[Session, Depends(get_session)]) -> dict:
    """Se há 2º turno por disputar, a data e os estados com 2º turno para governador."""
    return segundo_turno.agenda(session)


@router.get("/segundo-turno", response_model=SegundoTurnoResposta)
def comparar(
    session: Annotated[Session, Depends(get_session)],
    cep: Annotated[str | None, Query(description="CEP com ou sem hífen")] = None,
    uf: Annotated[str | None, Query(description="Sigla da UF, se não souber o CEP")] = None,
    municipio: Annotated[str | None, Query(description="Código IBGE do município")] = None,
) -> dict:
    """Presidente e, se o estado tiver 2º turno, governador: os mesmos campos para cada
    candidato, na ordem do número na urna. Campo sem dado vem nulo."""
    localizacao = localizar(session, cep, uf, municipio)
    return {"localizacao": localizacao, **segundo_turno.comparar(session, localizacao.uf)}
