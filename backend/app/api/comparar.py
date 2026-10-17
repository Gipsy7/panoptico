from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import MandatoLocal, Parlamentar
from app.schemas import (
    ComparacaoLocal,
    ComparacaoLocalN,
    ComparacaoNResposta,
    ComparacaoResposta,
)
from app.services import camaras, comparar, ranking

router = APIRouter()

MIN_PESSOAS = 2
MAX_PESSOAS = 4


def _ler_ids(ids: str) -> list[int]:
    """'1,2,3' -> [1, 2, 3]; 422 com mensagem clara se mal formado, repetido ou fora de 2 a 4."""
    try:
        lista = [int(x) for x in ids.split(",")]
    except ValueError:
        raise HTTPException(
            422, "ids deve ser uma lista de números separados por vírgula."
        ) from None
    if len(set(lista)) != len(lista):
        raise HTTPException(422, "Escolha pessoas diferentes: há ids repetidos.")
    if not MIN_PESSOAS <= len(lista) <= MAX_PESSOAS:
        raise HTTPException(422, f"Escolha de {MIN_PESSOAS} a {MAX_PESSOAS} pessoas.")
    return lista


def _escolhidos(ids: str | None, a: int | None, b: int | None) -> tuple[list[int], bool]:
    """Devolve os ids e se a chamada usou `ids` (forma nova). `a`/`b` seguem como alias."""
    if ids is not None:
        if a is not None or b is not None:
            raise HTTPException(422, "Use ids ou a e b, não os dois.")
        return _ler_ids(ids), True
    if a is None or b is None:
        raise HTTPException(422, "Informe ids (de 2 a 4 pessoas) ou a e b.")
    return _ler_ids(f"{a},{b}"), False


@router.get("/comparar", response_model=ComparacaoNResposta | ComparacaoResposta)
def comparar_parlamentares(
    session: Annotated[Session, Depends(get_session)],
    ids: Annotated[str | None, Query(description="De 2 a 4 ids separados por vírgula")] = None,
    a: Annotated[int | None, Query(description="Alias antigo: primeiro id")] = None,
    b: Annotated[int | None, Query(description="Alias antigo: segundo id")] = None,
    ano: Annotated[int | None, Query(description="Padrão: ano mais recente")] = None,
) -> dict:
    """Com `ids`, a resposta é a nova forma (`pessoas`, `numeros`...). Com `a` e `b`, a forma
    antiga, igual à de sempre."""
    lista, novo = _escolhidos(ids, a, b)
    pessoas = [session.get(Parlamentar, i) for i in lista]
    if any(p is None for p in pessoas):
        raise HTTPException(404, "Parlamentar não encontrado.")
    anos = ranking.anos_disponiveis(session)
    if not anos:
        raise HTTPException(404, "Os números ainda não foram calculados.")
    if ano is None:
        ano = anos[0]
    elif ano not in anos:
        raise HTTPException(404, f"Sem números para {ano}.")
    if novo:
        return comparar.comparar_n(session, pessoas, ano)
    return comparar.comparar(session, pessoas[0], pessoas[1], ano)


@router.get("/comparar/local", response_model=ComparacaoLocalN | ComparacaoLocal)
def comparar_locais(
    session: Annotated[Session, Depends(get_session)],
    ids: Annotated[str | None, Query(description="De 2 a 4 ids separados por vírgula")] = None,
    a: Annotated[int | None, Query(description="Alias antigo: primeiro id")] = None,
    b: Annotated[int | None, Query(description="Alias antigo: segundo id")] = None,
) -> dict:
    """De 2 a 4 vereadores da mesma câmara, ou deputados da mesma assembleia, lado a lado.
    Só na mesma casa: as pautas de casas diferentes não são comparáveis. Com `ids`, forma
    nova; com `a` e `b`, a forma antiga."""
    lista, novo = _escolhidos(ids, a, b)
    mandatos = [session.get(MandatoLocal, i) for i in lista]
    if any(m is None for m in mandatos):
        raise HTTPException(404, "Vereador ou deputado não encontrado.")
    if not all(camaras.mesma_casa(mandatos[0], m) for m in mandatos[1:]):
        raise HTTPException(422, "Só dá para comparar pessoas da mesma câmara ou assembleia.")
    if novo:
        return camaras.comparar_n(session, mandatos)
    return camaras.comparar(session, mandatos[0], mandatos[1])
