"""Ficha do fornecedor por CNPJ: só leitura, só somas e contagens.

Regras em app/services/ficha_fornecedor.py.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from app.db import Sessao
from app.services import ficha_fornecedor

router = APIRouter()


@router.get("/fornecedores/{cnpj}")
def ficha_do_fornecedor(
    session: Sessao,
    # Com ou sem pontuação; a barra do CNPJ formatado não cabe num segmento de endereço.
    cnpj: Annotated[str, Path(pattern=r"^[0-9.\-]{14,18}$")],
) -> dict:
    ficha = ficha_fornecedor.ficha(session, cnpj)
    if ficha is None:
        raise HTTPException(404, "CNPJ inválido ou sem registro nos dados do site.")
    return ficha
