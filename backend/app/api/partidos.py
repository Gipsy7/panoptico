from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import PartidoDetalheResposta, PartidosResposta
from app.services import partidos

router = APIRouter()


@router.get("/partidos", response_model=PartidosResposta)
def listar_partidos(
    session: Annotated[Session, Depends(get_session)], ano: Annotated[int | None, Query()] = None
) -> dict:
    """Cotas, receita, gasto e repasses de cada partido numa prestação de contas anual."""
    anos = partidos.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Sem contas de partidos carregadas.")
    escolhido = ano if ano is not None else anos[0]
    if escolhido not in anos:
        raise HTTPException(404, f"Sem contas de partidos para {escolhido}.")
    return partidos.listar(session, escolhido)


@router.get("/partidos/{sigla}", response_model=PartidoDetalheResposta)
def detalhe_do_partido(
    sigla: str,
    session: Annotated[Session, Depends(get_session)],
    ano: Annotated[int | None, Query()] = None,
) -> dict:
    """De onde veio o dinheiro do partido e em que gastou, com as transferências à parte."""
    do_banco = partidos.sigla_do_banco(session, sigla)
    if do_banco is None:
        raise HTTPException(404, "Partido não encontrado.")
    anos = partidos.anos_disponiveis(session, do_banco)
    escolhido = ano if ano is not None else anos[0]
    if escolhido not in anos:
        raise HTTPException(404, f"Sem contas deste partido em {escolhido}.")
    resultado = partidos.detalhe(session, do_banco, escolhido)
    if resultado is None:
        raise HTTPException(404, f"Sem contas deste partido em {escolhido}.")
    return resultado
