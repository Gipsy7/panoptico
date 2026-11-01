"""Painel privado de acessos: entrar com usuário e senha e ler o resumo agregado.

Sem PAINEL_USUARIO, PAINEL_SENHA_HASH e PAINEL_SEGREDO, tudo responde 503. As respostas nunca vão
para o cache (o middleware de app/main.py põe "no-store" em /painel). Erro de login é sempre o
mesmo, e as tentativas erradas por IP são contadas só na memória.
"""

import hmac
import time
from collections import defaultdict, deque
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.metricas import origem_do_pedido
from app.config import settings
from app.db import get_session
from app.services import metricas as servico
from app.services import painel_auth

router = APIRouter(prefix="/painel")

TENTATIVAS = 5
JANELA_S = 15 * 60
_erros: dict[str, deque[float]] = defaultdict(deque)
# Hash de uma senha que ninguém tem, para gastar o mesmo tempo quando o usuário não confere.
_HASH_FALSO = painel_auth.gerar_hash("nao-e-a-senha")


class Credenciais(BaseModel):
    usuario: str = Field(max_length=100)
    senha: str = Field(max_length=200)


def _configurado() -> bool:
    return bool(settings.painel_usuario and settings.painel_senha_hash and settings.painel_segredo)


def _exigir_configurado() -> None:
    if not _configurado():
        raise HTTPException(503, "Painel não configurado.")


def _erros_recentes(ip: str) -> deque[float]:
    agora = time.monotonic()
    fila = _erros[ip]
    while fila and agora - fila[0] > JANELA_S:
        fila.popleft()
    if len(_erros) > 5000:
        for chave in [k for k, f in _erros.items() if not f or agora - f[-1] > JANELA_S]:
            del _erros[chave]
    return fila


@router.post("/entrar", dependencies=[Depends(_exigir_configurado)])
def entrar(corpo: Credenciais, request: Request) -> dict:
    ip = origem_do_pedido(request)
    fila = _erros_recentes(ip)
    if len(fila) >= TENTATIVAS:
        raise HTTPException(429, "Muitas tentativas. Tente de novo mais tarde.")
    usuario_ok = hmac.compare_digest(corpo.usuario.encode(), settings.painel_usuario.encode())
    senha_ok = painel_auth.conferir_senha(
        corpo.senha, settings.painel_senha_hash if usuario_ok else _HASH_FALSO
    )
    if not (usuario_ok and senha_ok):
        fila.append(time.monotonic())
        raise HTTPException(401, "Usuário ou senha incorretos.")
    fila.clear()
    return {
        "token": painel_auth.emitir_token(settings.painel_segredo),
        "expira_em_segundos": painel_auth.VALIDADE_S,
    }


def exigir_token(authorization: Annotated[str | None, Header()] = None) -> None:
    _exigir_configurado()
    prefixo = "Bearer "
    if not authorization or not authorization.startswith(prefixo):
        raise HTTPException(401, "Entre de novo.")
    if not painel_auth.token_valido(authorization[len(prefixo) :], settings.painel_segredo):
        raise HTTPException(401, "Entre de novo.")


@router.get("/resumo", dependencies=[Depends(exigir_token)])
def resumo(
    session: Annotated[Session, Depends(get_session)],
    dias: Annotated[int, Query(ge=1, le=90)] = 7,
    aparelho: Literal["celular", "computador"] | None = None,
    origem: Literal["direto", "whatsapp", "google", "buscadores", "redes", "outro_site"]
    | None = None,
    uf: Annotated[str | None, Query(pattern=r"^[A-Z]{2}$")] = None,
    item: Annotated[str | None, Query(max_length=130)] = None,
) -> dict:
    if uf is not None and uf not in servico.UFS:
        raise HTTPException(422, "UF desconhecida.")
    return servico.resumo(session, dias, aparelho, origem, uf, item)
