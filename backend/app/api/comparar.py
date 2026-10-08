from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import MandatoLocal, Parlamentar
from app.schemas import ComparacaoLocal, ComparacaoResposta
from app.services import camaras, comparar, ranking

router = APIRouter()


@router.get("/comparar", response_model=ComparacaoResposta)
def comparar_parlamentares(
    session: Annotated[Session, Depends(get_session)],
    a: Annotated[int, Query(description="Id do primeiro parlamentar")],
    b: Annotated[int, Query(description="Id do segundo parlamentar")],
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente")] = None,
) -> dict:
    if a == b:
        raise HTTPException(422, "Escolha dois parlamentares diferentes.")
    pa, pb = session.get(Parlamentar, a), session.get(Parlamentar, b)
    if pa is None or pb is None:
        raise HTTPException(404, "Parlamentar não encontrado.")
    anos = ranking.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Os números ainda não foram calculados.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem números para {ano}.")
    return comparar.comparar(session, pa, pb, ano)


@router.get("/comparar/local", response_model=ComparacaoLocal)
def comparar_locais(
    session: Annotated[Session, Depends(get_session)],
    a: Annotated[int, Query(description="Id do primeiro vereador ou deputado estadual")],
    b: Annotated[int, Query(description="Id do segundo, da mesma câmara ou assembleia")],
) -> dict:
    """Dois vereadores da mesma câmara, ou dois deputados da mesma assembleia, lado a lado.
    Só na mesma casa: as pautas de casas diferentes não são comparáveis."""
    if a == b:
        raise HTTPException(422, "Escolha duas pessoas diferentes.")
    ma, mb = session.get(MandatoLocal, a), session.get(MandatoLocal, b)
    if ma is None or mb is None:
        raise HTTPException(404, "Vereador ou deputado não encontrado.")
    if not camaras.mesma_casa(ma, mb):
        raise HTTPException(422, "Só dá para comparar duas pessoas da mesma câmara ou assembleia.")
    return camaras.comparar(session, ma, mb)
