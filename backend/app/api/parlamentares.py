from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Parlamentar
from app.schemas import (
    GastosResposta,
    ListaParlamentaresResposta,
    ParlamentarDetalhe,
    PresencaResposta,
    ProjetosResposta,
    TemasResposta,
    VotosResposta,
)
from app.services import gastos, presenca, projetos, ranking, remuneracao, temas, votos

router = APIRouter()


def _buscar(session: Session, parlamentar_id: int) -> Parlamentar:
    encontrado = session.get(Parlamentar, parlamentar_id)
    if encontrado is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    return encontrado


@router.get("/parlamentares", response_model=ListaParlamentaresResposta)
def lista_de_parlamentares(
    session: Annotated[Session, Depends(get_session)],
    busca: Annotated[str | None, Query(description="Parte do nome")] = None,
    casa: Literal["camara", "senado"] | None = None,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    partido: str | None = None,
    ordenar: Literal[
        "nome", "gastos", "presenca", "projetos", "normas", "emendas", "governo"
    ] = "nome",
    ordem: Literal["asc", "desc"] = "asc",
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    anos = ranking.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Os números ainda não foram calculados.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem números para {ano}.")
    return ranking.listar(
        session, ano=ano, busca=busca, casa=casa, uf=uf, partido=partido,
        ordenar=ordenar, ordem=ordem, pagina=pagina,
    )  # fmt: skip


@router.get("/parlamentares/{parlamentar_id}", response_model=ParlamentarDetalhe)
def parlamentar(
    parlamentar_id: int, session: Annotated[Session, Depends(get_session)]
) -> ParlamentarDetalhe:
    p = _buscar(session, parlamentar_id)
    colunas = {c.key: getattr(p, c.key) for c in Parlamentar.__table__.columns}
    return ParlamentarDetalhe.model_validate({**colunas, "remuneracao": remuneracao.vigente()})


@router.get("/parlamentares/{parlamentar_id}/gastos", response_model=GastosResposta)
def gastos_do_parlamentar(
    parlamentar_id: int,
    session: Annotated[Session, Depends(get_session)],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente com dados")] = None,
) -> dict:
    p = _buscar(session, parlamentar_id)
    anos = gastos.anos_disponiveis(session, p)
    if not anos:
        raise HTTPException(404, "Ainda não há gastos carregados para esta Casa.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem gastos carregados para {ano}.")
    return gastos.resumo(session, p, ano)


@router.get("/parlamentares/{parlamentar_id}/projetos", response_model=ProjetosResposta)
def projetos_do_parlamentar(
    parlamentar_id: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    return projetos.resumo(session, _buscar(session, parlamentar_id))


@router.get("/parlamentares/{parlamentar_id}/presenca", response_model=PresencaResposta)
def presenca_do_parlamentar(
    parlamentar_id: int,
    session: Annotated[Session, Depends(get_session)],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente com dados")] = None,
) -> dict:
    p = _buscar(session, parlamentar_id)
    anos = presenca.anos_disponiveis(session, p.casa)
    if not anos:
        raise HTTPException(404, "Ainda não há votações carregadas para esta Casa.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem votações carregadas para {ano}.")
    return presenca.resumo(session, p, ano)


@router.get("/parlamentares/{parlamentar_id}/temas", response_model=TemasResposta)
def temas_do_parlamentar(
    parlamentar_id: int, session: Annotated[Session, Depends(get_session)]
) -> dict:
    return temas.projetos_por_tema(session, _buscar(session, parlamentar_id))


@router.get("/parlamentares/{parlamentar_id}/votos", response_model=VotosResposta)
def votos_do_parlamentar(
    parlamentar_id: int,
    session: Annotated[Session, Depends(get_session)],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente com dados")] = None,
    tema: Annotated[str | None, Query(description="Tema oficial da proposição votada")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> dict:
    p = _buscar(session, parlamentar_id)
    anos = presenca.anos_disponiveis(session, p.casa)
    if not anos:
        raise HTTPException(404, "Ainda não há votações carregadas para esta Casa.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem votações carregadas para {ano}.")

    resumo = ranking.resumo_de(session, p, ano)
    lista = ranking.listar(session, ano=ano, casa=p.casa)
    fonte = presenca.FONTES[p.casa]

    def placar(iguais: int, total: int) -> dict:
        return {"iguais": iguais, "total": total, "percentual": ranking._pct(iguais, total)}

    return {
        "ano": ano,
        "anos_disponiveis": anos,
        "governo": placar(resumo["governo_iguais"], resumo["governo_total"])
        if resumo and p.casa == "camara"
        else None,
        "partido": placar(resumo["partido_iguais"], resumo["partido_total"])
        if resumo
        else placar(0, 0),
        "media_governo": lista["medias"][p.casa]["governo"],
        "media_partido": ranking.media_partido(session, p.casa, ano),
        "temas_disponiveis": votos.temas_disponiveis(session, p, ano),
        "tema": tema,
        **votos.lista_votos(session, p, ano, tema, pagina),
        "fonte_nome": fonte["nome"],
        "fonte_url": fonte["url"],
        "atualizado_em": lista["atualizado_em"],
    }
