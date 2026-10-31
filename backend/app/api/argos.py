"""Rotas de registro do chat Argos (só POST; nenhuma rota lê esses dados).

Resposta 204 sempre que o pedido é válido, inclusive com ARGOS_REGISTRO desligado (o site
nunca deve quebrar por causa do registro). O limite de pedidos por IP vive só na memória do
processo: o IP não é gravado em lugar nenhum.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.limite import LimitePorOrigem
from app.config import settings
from app.db import get_session
from app.services import argos as servico

router = APIRouter(prefix="/argos")

LIMITE_POR_MINUTO = 20
limitar = LimitePorOrigem(LIMITE_POR_MINUTO)
_pedidos = limitar.pedidos


class NaoEntendida(BaseModel):
    texto: str = Field(min_length=1, max_length=servico.MAX_FRASE)


class Mensagem(BaseModel):
    autor: Literal["cidadao", "argos"]
    texto: str = Field(max_length=servico.MAX_MENSAGEM)


class Avaliacao(BaseModel):
    util: bool
    assunto: str = Field(min_length=1, max_length=40, pattern=r"^[a-z_]+$")
    # Só vai quando a pessoa respondeu "Pode guardar".
    conversa: list[Mensagem] | None = Field(default=None, max_length=servico.MAX_MENSAGENS)


def _sem_cache(resposta: Response) -> None:
    resposta.headers["Cache-Control"] = "no-store"


@router.post("/nao-entendida", status_code=204, dependencies=[Depends(limitar)])
def nao_entendida(
    corpo: NaoEntendida, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> None:
    _sem_cache(resposta)
    if settings.argos_registro:
        servico.registrar_nao_entendida(session, corpo.texto)


@router.post("/avaliacao", status_code=204, dependencies=[Depends(limitar)])
def avaliacao(
    corpo: Avaliacao, session: Annotated[Session, Depends(get_session)], resposta: Response
) -> None:
    _sem_cache(resposta)
    if settings.argos_registro:
        conversa = [m.model_dump() for m in corpo.conversa] if corpo.conversa else None
        servico.registrar_avaliacao(session, corpo.util, corpo.assunto, conversa)
