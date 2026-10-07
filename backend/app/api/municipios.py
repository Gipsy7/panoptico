from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Municipio
from app.schemas import EmendasMunicipioResposta, MunicipioInfo
from app.services import emendas

router = APIRouter()


@router.get("/municipios/{ibge}/emendas", response_model=EmendasMunicipioResposta)
def emendas_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return emendas.resumo_municipio(session, municipio)


@router.get("/municipios", response_model=list[MunicipioInfo])
def municipios_da_uf(
    uf: Annotated[str, Query(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Municipio]:
    return list(
        session.scalars(
            select(Municipio).where(Municipio.uf == uf.upper()).order_by(Municipio.nome_chave)
        )
    )
