from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import CanalOficial, Municipio
from app.schemas import (
    CanaisResposta,
    ContasMunicipioResposta,
    EmendasMunicipioResposta,
    MunicipioInfo,
)
from app.services import contas, emendas

router = APIRouter()


@router.get("/municipios/{ibge}/emendas", response_model=EmendasMunicipioResposta)
def emendas_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    municipio = session.get(Municipio, ibge)
    if municipio is None:
        raise HTTPException(404, "Município não encontrado.")
    return emendas.resumo_municipio(session, municipio)


@router.get("/municipios/{ibge}/contas", response_model=ContasMunicipioResposta)
def contas_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Contas anuais da prefeitura no SICONFI: receita, despesa e áreas."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    resultado = contas.resumo(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem contas entregues ao Tesouro para este município.")
    return resultado


ORDEM_CANAIS = ["prefeitura", "camara", "sapl", "transparencia_prefeitura", "transparencia_camara"]


@router.get("/municipios/{ibge}/canais", response_model=CanaisResposta)
def canais_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Sites oficiais da cidade, do catálogo revisado (data/canais_oficiais.csv)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    canais = session.scalars(select(CanalOficial).where(CanalOficial.municipio_ibge == ibge)).all()
    canais = sorted(
        canais, key=lambda c: ORDEM_CANAIS.index(c.tipo) if c.tipo in ORDEM_CANAIS else 99
    )
    return {"itens": canais}


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
