"""Avisar erro, direito de resposta e correções públicas (docs/DECISOES.md, 2026-11-07).

O POST grava na fila de revisão humana; nada muda no site sem uma pessoa conferir com a fonte.
O limite de 5 por hora por origem vive só na memória do processo: o IP não é gravado em lugar
nenhum. As rotas de leitura mostram só o que é público (nunca o contato nem quem avisou).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.limite import LimitePorOrigem
from app.db import Sessao
from app.schemas.sugestoes import Correcoes, Protocolo, RespostaPublicada, SugestaoEntrada
from app.services import sugestoes as servico

router = APIRouter()

LIMITE_POR_HORA = 5
limitar = LimitePorOrigem(
    LIMITE_POR_HORA,
    janela=3600,
    mensagem="Você já mandou 5 avisos na última hora. Tente de novo mais tarde.",
)
_pedidos = limitar.pedidos


@router.post("/sugestoes", status_code=201, response_model=Protocolo)
def enviar(
    corpo: SugestaoEntrada,
    session: Sessao,
    resposta: Response,
    _: Annotated[None, Depends(limitar)],
) -> dict:
    """Aviso de erro ou resposta de quem é citado. Devolve o protocolo para acompanhar."""
    resposta.headers["Cache-Control"] = "no-store"
    return {"protocolo": servico.criar(session, corpo.model_dump())}


# Antes de /pessoas/{pessoa_id} (o router de pessoas vem depois em app/main.py).
@router.get("/pessoas/de/respostas", response_model=list[RespostaPublicada])
def respostas(
    tipo: str,
    id: Annotated[str, Query(min_length=1, max_length=40)],
    session: Sessao,
) -> list[dict]:
    """Respostas de quem é citado já publicadas no perfil. Lista vazia se não houver."""
    return servico.respostas_publicadas(session, tipo, id)


@router.get("/correcoes", response_model=Correcoes)
def correcoes(
    session: Sessao,
    tipo: str | None = None,
    id: Annotated[str | None, Query(max_length=40)] = None,
) -> dict:
    """Correções feitas a partir de avisos, da mais recente à mais antiga."""
    return servico.correcoes(session, tipo, id)
