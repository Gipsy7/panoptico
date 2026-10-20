from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Municipio
from app.schemas import DinheiroFederalEstado, DinheiroFederalMunicipio, DinheiroFederalPainel
from app.services import dinheiro_federal as servico

router = APIRouter()

AnoQuery = Annotated[int, Query(description="Ano de referência (2019 até o ano em curso).")]


def _validar_ano(ano: int) -> int:
    if ano not in servico.anos_disponiveis():
        raise HTTPException(404, "Sem dados para este ano.")
    return ano


@router.get("/dinheiro-federal", response_model=DinheiroFederalPainel)
def painel(session: Annotated[Session, Depends(get_session)], ano: AnoQuery = servico.ANO_PADRAO):
    """Arrecadação federal e repasses da União, no Brasil e em cada estado."""
    return servico.painel(session, _validar_ano(ano))


@router.get("/dinheiro-federal/{uf}", response_model=DinheiroFederalEstado)
def estado(
    uf: str,
    session: Annotated[Session, Depends(get_session)],
    ano: AnoQuery = servico.ANO_PADRAO,
):
    """Totais do estado e repasses a cada cidade."""
    _validar_ano(ano)
    resultado = servico.estado(session, uf.upper(), ano)
    if resultado is None:
        raise HTTPException(404, "Estado não encontrado.")
    return resultado


@router.get("/municipios/{ibge}/dinheiro-federal", response_model=DinheiroFederalMunicipio)
def do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]):
    """Repasses da União à cidade por ano e quanto da receita da prefeitura vem deles."""
    mun = session.get(Municipio, ibge)
    if mun is None:
        raise HTTPException(404, "Município não encontrado.")
    return servico.municipio(session, mun)
