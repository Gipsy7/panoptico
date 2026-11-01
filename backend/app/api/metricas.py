"""Contagem anônima de acessos (só POST; nenhuma rota pública lê esses dados).

O navegador manda um beacon (text/plain, sem preflight de CORS) a cada página e a cada uso de
um recurso. Responde 204 sempre, inclusive quando a contagem está desligada, no release ou o corpo
é inválido: o site nunca deve quebrar nem "avisar" o visitante por causa disso. O limite de pedidos
por IP vive só na memória do processo; o IP e o user-agent não são gravados em lugar nenhum.
"""

import json
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.services import metricas as servico

router = APIRouter(prefix="/metricas")

LIMITE_POR_MINUTO = 120
MAX_CORPO = 1024
_pedidos: dict[str, deque[float]] = defaultdict(deque)


def origem_do_pedido(request: Request) -> str:
    """IP de quem pediu (atrás do Cloudflare vem no cabeçalho), só para contar na memória."""
    return (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "?")
    )


def _dentro_do_limite(request: Request) -> bool:
    agora = time.monotonic()
    fila = _pedidos[origem_do_pedido(request)]
    while fila and agora - fila[0] > 60:
        fila.popleft()
    if len(fila) >= LIMITE_POR_MINUTO:
        return False
    fila.append(agora)
    if len(_pedidos) > 5000:  # não cresce sem limite
        for chave in [k for k, f in _pedidos.items() if not f or agora - f[-1] > 60]:
            del _pedidos[chave]
    return True


def contagem_ligada() -> bool:
    """Só a produção grava: o release usa o mesmo banco e não pode somar ao total."""
    return settings.metricas_ativas and settings.ambiente == "producao"


async def _tratar(request: Request, session: Session, gravar) -> None:
    if not contagem_ligada() or servico.eh_robo(request.headers.get("user-agent")):
        return
    origem = request.headers.get("origin")
    if origem and origem not in settings.cors_origins:
        return  # outro site mandando beacon para cá
    if not _dentro_do_limite(request):
        return
    try:
        bruto = await request.body()
        if len(bruto) > MAX_CORPO:
            return
        corpo = json.loads(bruto)
    except (ValueError, UnicodeDecodeError):
        return
    try:
        await run_in_threadpool(gravar, session, corpo)
    except Exception:  # noqa: BLE001 - a contagem nunca pode causar erro visível
        session.rollback()


@router.post("/visita", status_code=204)
async def visita(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    await _tratar(request, session, servico.registrar_visita)
    return Response(status_code=204)


@router.post("/recurso", status_code=204)
async def recurso(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    await _tratar(request, session, servico.registrar_recurso)
    return Response(status_code=204)


@router.post("/saida", status_code=204)
async def saida(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    await _tratar(request, session, servico.registrar_saida)
    return Response(status_code=204)


@router.post("/secao", status_code=204)
async def secao(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    await _tratar(request, session, servico.registrar_secao)
    return Response(status_code=204)


@router.post("/busca", status_code=204)
async def busca(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    await _tratar(request, session, servico.registrar_busca)
    return Response(status_code=204)
