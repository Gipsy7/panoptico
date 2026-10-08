"""Eleitos que só existem no TSE: vereadores e deputados estaduais e distritais."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Candidatura, Municipio
from app.schemas import EleitoDetalhe, ListaEleitos
from app.services import tse
from app.services.representantes import UFS

router = APIRouter()


@router.get("/municipios/{ibge}/vereadores", response_model=ListaEleitos)
def vereadores_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return tse.vereadores(session, ibge)


@router.get("/estados/{uf}/deputados-estaduais", response_model=ListaEleitos)
def deputados_estaduais(
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    return tse.deputados_estaduais(session, uf)


@router.get("/eleitos/{candidatura_id}", response_model=EleitoDetalhe)
def eleito(candidatura_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    candidatura = session.get(Candidatura, candidatura_id)
    if candidatura is None or candidatura.cargo not in ("VEREADOR", *tse.CARGOS_ESTADUAIS):
        raise HTTPException(404, "Eleito não encontrado.")
    return tse.eleito(session, candidatura)
