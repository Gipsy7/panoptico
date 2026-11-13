from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.db import Sessao
from app.schemas import PartidoDetalheResposta, PartidosResposta
from app.schemas.bancadas import CadeirasPorPartido
from app.services import bancadas, partidos

router = APIRouter()


@router.get("/partidos", response_model=PartidosResposta)
def listar_partidos(session: Sessao, ano: Annotated[int | None, Query()] = None) -> dict:
    """Cotas, receita, gasto e repasses de cada partido numa prestação de contas anual."""
    anos = partidos.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Sem contas de partidos carregadas.")
    escolhido = ano if ano is not None else anos[0]
    if escolhido not in anos:
        raise HTTPException(404, f"Sem contas de partidos para {escolhido}.")
    return partidos.listar(session, escolhido)


@router.get("/partidos/cadeiras", response_model=CadeirasPorPartido)
def cadeiras_dos_partidos(session: Sessao) -> dict:
    """Deputados e senadores no cargo, prefeitos e vereadores eleitos, por partido."""
    return bancadas.cadeiras_por_partido(session)


@router.get("/partidos/{sigla}", response_model=PartidoDetalheResposta)
def detalhe_do_partido(
    sigla: str,
    session: Sessao,
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
