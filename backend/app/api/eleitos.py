"""Eleitos que só existem no TSE: vereadores e deputados estaduais e distritais."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Candidatura, MandatoLocal, Municipio
from app.schemas import (
    CamaraResposta,
    EleitoDetalhe,
    EleitosFuturos,
    Executivo,
    ListaEleitos,
    VereadorDetalhe,
    VotacoesLocais,
)
from app.services import camaras, eleitos_futuros, tse
from app.services.representantes import UFS

router = APIRouter()


@router.get("/municipios/{ibge}/vereadores", response_model=ListaEleitos)
def vereadores_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    if session.get(Municipio, ibge) is None:
        raise HTTPException(404, "Município não encontrado.")
    return tse.vereadores(session, ibge)


@router.get("/municipios/{ibge}/camara", response_model=CamaraResposta)
def camara_do_municipio(ibge: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Vereadores no cargo hoje, segundo a própria câmara (só onde há conector)."""
    resultado = camaras.camara(session, ibge)
    if resultado is None:
        raise HTTPException(404, "Sem dados da câmara deste município.")
    return resultado


@router.get("/estados/{uf}/assembleia", response_model=CamaraResposta)
def assembleia_do_estado(uf: str, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Deputados estaduais no cargo hoje, segundo a própria assembleia (só onde há conector)."""
    resultado = camaras.assembleia(session, uf.upper())
    if resultado is None:
        raise HTTPException(404, "Sem dados da própria assembleia para este estado.")
    return resultado


@router.get("/vereadores/{mandato_id}", response_model=VereadorDetalhe)
def vereador(mandato_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    mandato = session.get(MandatoLocal, mandato_id)
    if mandato is None:
        raise HTTPException(404, "Vereador não encontrado.")
    return camaras.vereador(session, mandato)


@router.get("/estados/{uf}/deputados-estaduais", response_model=ListaEleitos)
def deputados_estaduais(
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    return tse.deputados_estaduais(session, uf)


@router.get("/estados/{uf}/eleitos-2026", response_model=EleitosFuturos)
def eleitos_2026_do_estado(
    uf: Annotated[str, Path(min_length=2, max_length=2)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Eleitos de 2026 que ainda não tomaram posse (e quem disputa o 2º turno), à parte de
    quem está no cargo hoje."""
    if uf.upper() not in UFS:
        raise HTTPException(404, "Estado não encontrado.")
    return eleitos_futuros.do_estado(session, uf)


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
    # Deputados federais e senadores só têm perfil de eleito antes da posse; depois, o perfil
    # de parlamentar (com a atividade) assume.
    aceito = candidatura is not None and (
        candidatura.cargo in tse.CARGOS_COM_PERFIL
        or (
            candidatura.cargo in ("DEPUTADO FEDERAL", "SENADOR")
            and candidatura.ano_eleicao >= date.today().year
        )
    )
    if candidatura is None or not aceito:
        raise HTTPException(404, "Eleito não encontrado.")
    return tse.eleito(session, candidatura)


@router.get("/vereadores/{mandato_id}/votacoes", response_model=VotacoesLocais)
def votacoes_do_vereador(
    mandato_id: int,
    session: Annotated[Session, Depends(get_session)],
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    """Como votou nas votações nominais da câmara ou da assembleia (ano atual e anterior)."""
    mandato = session.get(MandatoLocal, mandato_id)
    if mandato is None:
        raise HTTPException(404, "Vereador não encontrado.")
    return camaras.votacoes(session, mandato, pagina)
