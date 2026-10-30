"""Rotas dos avisos por Web Push (só POST, sem cache).

Com avisos desligados ou sem chave, tudo responde 503 sem tocar no banco: é o que mantém produção
e reserva fora do recurso. O corpo nunca vai para log.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.limite import LimitePorOrigem
from app.db import get_session
from app.models import AvisoInscricao
from app.services import avisos as servico

router = APIRouter(prefix="/avisos")

LIMITE_POR_MINUTO = 60  # mais folgado que o do Argos: operadoras de celular dividem IP
SEM_CACHE = {"Cache-Control": "no-store"}
BASE64URL = r"^[A-Za-z0-9_-]+={0,2}$"

_limite = LimitePorOrigem(LIMITE_POR_MINUTO)


class Aparelho(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    auth: str = Field(min_length=16, max_length=64, pattern=BASE64URL)

    @field_validator("endpoint")
    @classmethod
    def _endpoint(cls, valor: str) -> str:
        if not servico.endpoint_permitido(valor):
            raise ValueError("endpoint_nao_permitido")
        return valor


class Inscrever(Aparelho):
    p256dh: str = Field(min_length=64, max_length=256, pattern=BASE64URL)


class Alvo(Aparelho):
    alvo_tipo: Literal["parlamentar", "projeto"]
    alvo_chave: str = Field(pattern=r"^(camara|senado):[A-Za-z0-9_-]{1,30}$")
    acao: Literal["adicionar", "remover"]


def _erro(status: int, detalhe: str) -> HTTPException:
    return HTTPException(status, detalhe, headers=SEM_CACHE)


def exigir_ligado() -> None:
    if not servico.ligado():
        raise _erro(503, "avisos_desligados")


def limitar(request: Request) -> None:
    try:
        _limite(request)
    except HTTPException as erro:
        erro.headers = SEM_CACHE
        raise


GUARDAS = [Depends(exigir_ligado), Depends(limitar)]


def _sem_cache(resposta: Response) -> None:
    resposta.headers["Cache-Control"] = "no-store"


def _inscricao(session: Session, corpo: Aparelho, *, travar: bool = False) -> AvisoInscricao:
    inscricao = servico.buscar(session, corpo.endpoint, corpo.auth, travar=travar)
    if inscricao is None:
        raise _erro(404, "inscricao_nao_encontrada")
    return inscricao


@router.post("/inscrever", dependencies=GUARDAS)
def inscrever(
    corpo: Inscrever, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> dict:
    _sem_cache(resposta)
    if not servico.inscrever(session, corpo.endpoint, corpo.p256dh, corpo.auth):
        raise _erro(429, "limite_de_inscricoes")
    return {"ok": True}


@router.post("/alvo", dependencies=GUARDAS)
def alvo(
    corpo: Alvo, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> dict:
    _sem_cache(resposta)
    # Trava a linha da inscrição: dois pedidos juntos não passam do máximo de alvos.
    inscricao = _inscricao(session, corpo, travar=True)
    adicionar = corpo.acao == "adicionar"
    if adicionar and not servico.alvo_existe(session, corpo.alvo_tipo, corpo.alvo_chave):
        raise _erro(422, "alvo_inexistente")
    total = servico.alterar_alvo(session, inscricao, corpo.alvo_tipo, corpo.alvo_chave, adicionar)
    if total is None:
        raise _erro(429, "limite_de_alvos")
    return {"ok": True, "alvos": total}


@router.post("/cancelar", dependencies=GUARDAS)
def cancelar(
    corpo: Aparelho, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> dict:
    _sem_cache(resposta)
    servico.cancelar(session, _inscricao(session, corpo))
    return {"ok": True}


@router.post("/minhas", dependencies=GUARDAS)
def minhas(
    corpo: Aparelho, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> dict:
    _sem_cache(resposta)
    return servico.minhas(session, _inscricao(session, corpo))
