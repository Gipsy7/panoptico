"""Bancadas por partido: estado, município e composição do Congresso."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query

from app.db import Sessao
from app.models import Municipio
from app.schemas.bancadas import Bancada, BancadasEstado, ComposicaoCongresso
from app.services import bancadas
from app.services.representantes import UFS

router = APIRouter()


@router.get("/estados/{uf}/bancadas", response_model=BancadasEstado)
def bancadas_do_estado(
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    session: Sessao,
) -> dict:
    """Parlamentares no cargo por partido: assembleia, deputados federais e senadores do estado."""
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    return bancadas.do_estado(session, uf)


@router.get("/municipios/{ibge}/bancada", response_model=Bancada)
def bancada_do_municipio(ibge: str, session: Sessao) -> dict:
    """Vereadores por partido (os do cargo hoje; sem a câmara, os eleitos de 2024)."""
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return bancadas.do_municipio(session, ibge)


@router.get("/congresso/composicao", response_model=ComposicaoCongresso)
def composicao_do_congresso(
    session: Sessao,
    casa: Annotated[Literal["camara", "senado"], Query()] = "camara",
) -> dict:
    """Cadeiras por partido hoje e, havendo eleitos pendentes, a composição a partir de 2027."""
    return bancadas.composicao(session, casa)
