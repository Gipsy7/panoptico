from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Parlamentar
from app.schemas import GastosResposta, ParlamentarDetalhe, PresencaResposta, ProjetosResposta
from app.services import gastos, presenca, projetos, remuneracao

router = APIRouter()


def _buscar(session: Session, parlamentar_id: int) -> Parlamentar:
    encontrado = session.get(Parlamentar, parlamentar_id)
    if encontrado is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    return encontrado


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
