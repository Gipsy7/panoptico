"""Eleições completas (Frente 5): resultado de cada disputa, mais votados na cidade, eleitores e
quem teve o cargo antes."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.db import Sessao
from app.schemas.resultados_eleicao import (
    Antecessores,
    EleicaoDisponivel,
    Eleitores,
    MaisVotados,
    ResultadoEleicao,
)
from app.services import resultados_eleicao

router = APIRouter()


@router.get("/eleicoes/disponiveis", response_model=list[EleicaoDisponivel])
def disponiveis(session: Sessao) -> list[dict]:
    """Anos, cargos e turnos com resultado carregado."""
    return resultados_eleicao.disponiveis(session)


@router.get("/eleicoes/resultado", response_model=ResultadoEleicao)
def resultado(
    session: Sessao,
    ano: Annotated[int | None, Query()] = None,
    cargo: Annotated[str | None, Query(description="PRESIDENTE, GOVERNADOR, PREFEITO...")] = None,
    turno: Annotated[int | None, Query(ge=1, le=2)] = None,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio: Annotated[str | None, Query(description="Código IBGE")] = None,
    candidatura: Annotated[int | None, Query(description="Id da candidatura")] = None,
    limite: Annotated[int, Query(ge=1, le=2000)] = resultados_eleicao.LIMITE_PADRAO,
) -> dict:
    """Votos de cada candidato (do mais votado ao menos), comparecimento, brancos e nulos, e
    quem se elegeu nas eleições anteriores da mesma disputa. Com `candidatura`, a eleição dela.
    Com `municipio` num cargo de eleição geral (presidente, governador, senador), o recorte do
    município."""
    if candidatura is not None:
        r = resultados_eleicao.resultado_da_candidatura(session, candidatura)
    elif ano and cargo:
        r = resultados_eleicao.resultado(
            session, ano, cargo, turno, uf.upper() if uf else None, municipio, limite
        )
    else:
        raise HTTPException(422, "Informe ano e cargo, ou a candidatura.")
    if r is None:
        raise HTTPException(404, "Resultado não carregado para essa eleição.")
    return r


@router.get("/municipios/{ibge}/mais-votados", response_model=MaisVotados)
def mais_votados(
    ibge: str,
    session: Sessao,
    ano: Annotated[int | None, Query()] = None,
) -> dict:
    """Os 10 deputados mais votados no município (federal e estadual) e quanto dos votos daqui
    foram para quem se elegeu."""
    r = resultados_eleicao.mais_votados(session, ibge, ano)
    if r is None:
        raise HTTPException(404, "Resultado não carregado para esse município.")
    return r


@router.get("/municipios/{ibge}/eleitores", response_model=Eleitores)
def eleitores(ibge: str, session: Sessao) -> dict:
    """Moradores, eleitores aptos e quantos votaram na eleição mais recente carregada."""
    r = resultados_eleicao.eleitores(session, ibge)
    if r is None:
        raise HTTPException(404, "Eleitorado não carregado para esse município.")
    return r


@router.get("/eleicoes/antecessores", response_model=Antecessores)
def antecessores(
    session: Sessao,
    cargo: Annotated[str, Query()],
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio: Annotated[str | None, Query()] = None,
) -> dict:
    """Quem se elegeu para o cargo, eleição a eleição, na mesma cidade ou estado."""
    r = resultados_eleicao.antecessores(session, cargo, uf.upper() if uf else None, municipio)
    if r is None:
        raise HTTPException(404, "Nada carregado para esse cargo e lugar.")
    return r
