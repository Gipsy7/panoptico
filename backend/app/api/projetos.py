from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.projeto import (
    BuscaProjetos,
    Pauta,
    ProjetoDetalhe,
    ProjetoLocalDetalhe,
    VotacaoLocalDetalhe,
)
from app.services import pauta as servico_pauta
from app.services import projeto_detalhe, projetos_busca, votacao_local_detalhe

router = APIRouter()


@router.get("/projetos", response_model=BuscaProjetos)
def buscar_projetos(
    session: Annotated[Session, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    esfera: Literal["federal", "estadual", "municipal"] | None = None,
    casa: Literal["camara", "senado", "assembleia", "camara_municipal"] | None = None,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio: Annotated[str | None, Query(max_length=7)] = None,
    tema: Annotated[str | None, Query(max_length=100)] = None,
    ano: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    votacao: Literal["com", "sem"] | None = None,
    pagina: Annotated[int, Query(ge=1, le=10000)] = 1,
) -> dict:
    """Busca de projetos e votações. `q` aceita o número ("PL 2338/2023", "2338/2023") ou
    palavras da ementa (sem acento). Ordem: na pauta primeiro, depois a data da última votação
    ou movimentação, da mais recente para a mais antiga; 20 por página."""
    return projetos_busca.buscar(
        session, q, esfera, casa, uf, municipio, tema, ano, votacao, pagina
    )


# Rotas fixas antes das com parâmetro: "local" não é uma casa.
@router.get("/projetos/local/{projeto_local_id}", response_model=ProjetoLocalDetalhe)
def projeto_local(projeto_local_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Projeto de câmara municipal ou assembleia, com as votações nominais ligadas a ele."""
    dados = votacao_local_detalhe.projeto(session, projeto_local_id)
    if dados is None:
        raise HTTPException(404, "Projeto não encontrado.")
    return dados


@router.get("/projetos/{casa}/{id_externo}", response_model=ProjetoDetalhe)
def projeto_federal(
    casa: Literal["camara", "senado"],
    id_externo: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Um projeto do Congresso: ficha, votações nominais, quem votou, discursos, caminho e
    pauta, cada bloco com fonte e data. `id_externo` é o id da proposição na Casa."""
    dados = projeto_detalhe.detalhe(session, casa, id_externo)
    if dados is None:
        raise HTTPException(404, "Projeto não encontrado.")
    return dados


@router.get("/votacoes/local/{votacao_local_id}", response_model=VotacaoLocalDetalhe)
def votacao_local(votacao_local_id: int, session: Annotated[Session, Depends(get_session)]) -> dict:
    """Votação nominal de câmara municipal ou assembleia, como a casa publica."""
    dados = votacao_local_detalhe.votacao(session, votacao_local_id)
    if dados is None:
        raise HTTPException(404, "Votação não encontrada.")
    return dados


@router.get("/pauta", response_model=Pauta)
def pauta(
    session: Annotated[Session, Depends(get_session)],
    casa: Literal["camara", "senado"] | None = None,
    dias: Annotated[int, Query(ge=1, le=60)] = 14,
) -> dict:
    """Itens da pauta do Plenário nos próximos dias, por data."""
    return servico_pauta.pauta(session, casa, dias)
