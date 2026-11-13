"""Pessoa pública (a mesma em todas as fontes) e a linha do tempo dela."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.db import Sessao
from app.schemas import (
    CarreiraDaPessoa,
    CasoResposta,
    CasoResumo,
    ConfiancaDoPerfil,
    ContratosDaPessoa,
    LinhaDoTempo,
    PessoaDoPerfil,
    PessoaResposta,
    SancoesDaPessoa,
    ServicoFederalDaPessoa,
)
from app.services import confianca as confianca_servico
from app.services import contratos_pncp, cruzamentos, pessoas

router = APIRouter()

TipoDePerfil = Literal["parlamentar", "candidatura", "vereador", "deputado_estadual"]


# Antes de /pessoas/{pessoa_id}, senão "de" seria lido como id.
@router.get("/pessoas/de", response_model=PessoaDoPerfil)
def pessoa_de(
    tipo: TipoDePerfil,
    id: Annotated[int, Query(ge=1)],
    session: Sessao,
) -> dict:
    """A pessoa de um perfil do site (/parlamentar, /eleito, /vereador ou
    /deputado-estadual), para buscar a linha do tempo. 404 se o perfil não existe ou não
    está ligado a uma pessoa por vínculo forte ou revisado."""
    pessoa_id = pessoas.pessoa_de(session, tipo, id)
    if pessoa_id is None:
        raise HTTPException(404, "Pessoa não encontrada para este perfil.")
    return {"pessoa_id": pessoa_id}


@router.get("/pessoas/de/confianca", response_model=ConfiancaDoPerfil)
def confianca(
    tipo: TipoDePerfil,
    id: Annotated[int, Query(ge=1)],
    session: Sessao,
) -> dict:
    """Cabeçalho do perfil: quando o cadastro foi conferido com a fonte oficial, o fato
    oficial mais recente que temos e pessoas públicas com nome muito parecido. Funciona
    também para perfis sem pessoa ligada (aí não há fatos da linha do tempo)."""
    resultado = confianca_servico.do_perfil(session, tipo, id)
    if resultado is None:
        raise HTTPException(404, "Perfil não encontrado.")
    return resultado


@router.get("/pessoas/{pessoa_id}", response_model=PessoaResposta)
def pessoa(pessoa_id: int, session: Sessao) -> dict:
    """A pessoa e os perfis dela no site (mandato federal, na câmara ou assembleia, e
    candidaturas), só os ligados por chave forte ou revisados."""
    resultado = pessoas.pessoa(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/eventos", response_model=LinhaDoTempo)
def eventos(
    pessoa_id: int,
    session: Sessao,
    tipo: Annotated[str | None, Query(max_length=40)] = None,
    de: date | None = None,
    ate: date | None = None,
) -> dict:
    """Linha do tempo da pessoa, com a fonte oficial de cada fato."""
    resultado = pessoas.eventos(session, pessoa_id, tipo, de, ate)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/eventos.rss")
def eventos_feed(pessoa_id: int, request: Request, session: Sessao) -> Response:
    """Feed Atom 1.0 com os últimos 50 fatos oficiais da pessoa (eventos e eleições)."""
    base = str(request.base_url).rstrip("/")
    corpo = cruzamentos.feed_atom(
        session, pessoa_id, f"{base}/pessoas/{pessoa_id}/eventos.rss", f"{base}/pessoas/{pessoa_id}"
    )
    if corpo is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return Response(corpo, media_type="application/atom+xml")


@router.get("/pessoas/{pessoa_id}/sancoes", response_model=SancoesDaPessoa)
def sancoes(pessoa_id: int, session: Sessao) -> dict:
    """Sanções (CGU) e decisões do TCU ligadas à pessoa, com a regra da ligação."""
    resultado = cruzamentos.sancoes(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/servico-federal", response_model=ServicoFederalDaPessoa)
def servico_federal(pessoa_id: int, session: Sessao) -> dict:
    """Cargos de confiança, viagens a serviço e cartão de pagamento do governo federal."""
    resultado = cruzamentos.servico_federal(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/carreira", response_model=CarreiraDaPessoa)
def carreira(pessoa_id: int, session: Sessao) -> dict:
    """Todas as candidaturas ligadas à pessoa, com votos e bens declarados quando há."""
    resultado = cruzamentos.carreira(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/pessoas/{pessoa_id}/contratos", response_model=ContratosDaPessoa)
def contratos(pessoa_id: int, session: Sessao) -> dict:
    """Contratos públicos (PNCP) de empresas de que a pessoa é sócia, segundo o quadro de
    sócios da Receita Federal. Ser sócio de empresa contratada não é irregularidade."""
    resultado = contratos_pncp.da_pessoa(session, pessoa_id)
    if resultado is None:
        raise HTTPException(404, "Pessoa não encontrada.")
    return resultado


@router.get("/casos", response_model=list[CasoResumo])
def lista_de_casos(session: Sessao) -> list[dict]:
    """Casos montados com documentos oficiais (só os revisados; rascunhos não entram)."""
    return pessoas.casos(session)


@router.get("/casos/{slug}", response_model=CasoResposta)
def caso(slug: str, session: Sessao) -> dict:
    """Documentos oficiais do caso e o papel de cada pessoa segundo eles."""
    resultado = pessoas.caso(session, slug)
    if resultado is None:
        raise HTTPException(404, "Caso não encontrado.")
    return resultado
