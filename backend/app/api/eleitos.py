"""Eleitos que só existem no TSE: vereadores e deputados estaduais e distritais."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Candidatura, Municipio
from app.schemas import EleitoDetalhe, Executivo, ListaEleitos
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


@router.get("/executivo", response_model=Executivo)
def executivo(
    uf: Annotated[str, Query(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
    municipio: Annotated[str | None, Query(min_length=7, max_length=7)] = None,
) -> dict:
    """Presidente, governador do estado e, se houver município, o prefeito."""
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    return tse.executivo(session, uf, municipio)


@router.get("/fotos/{candidatura_id}.webp", response_class=Response)
def foto(candidatura_id: int, session: Annotated[Session, Depends(get_session)]) -> Response:
    """Foto do TSE. Não muda depois da eleição: a CDN guarda por um ano."""
    webp = tse.foto(session, candidatura_id)
    if webp is None:
        raise HTTPException(404, "Sem foto.")
    return Response(
        content=webp,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/eleitos/{candidatura_id}", response_model=EleitoDetalhe)
def eleito(candidatura_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    candidatura = session.get(Candidatura, candidatura_id)
    if candidatura is None or candidatura.cargo not in tse.CARGOS_COM_PERFIL:
        raise HTTPException(404, "Eleito não encontrado.")
    return tse.eleito(session, candidatura)
