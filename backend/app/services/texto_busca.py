"""Busca por palavras na ementa, sem acento e sem extensão do Postgres.

A mesma expressão vai no índice GIN (migração 0056) e na consulta, para o Postgres usar o
índice. `translate` e `lower` são IMMUTABLE, então a expressão serve de índice. O dicionário
`portuguese` faz o radical das palavras mas não tira acento; por isso o texto é normalizado
antes (tanto a ementa quanto o termo digitado). Ver docs/DECISOES.md, 2026-10-21."""

import re

ACENTUADAS = "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ"
SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucnaaaaaeeeeiiiiooooouuuucn"

_TABELA = str.maketrans(ACENTUADAS, SEM_ACENTO)


def sql_tsvector(coluna: str) -> str:
    """Expressão SQL do índice e da consulta para uma coluna de texto."""
    return f"to_tsvector('portuguese', translate(lower({coluna}), '{ACENTUADAS}', '{SEM_ACENTO}'))"


def normalizar(texto: str) -> str:
    """O mesmo que a expressão SQL faz com a coluna: minúsculas e sem acento."""
    return texto.translate(_TABELA).lower()


def palavras(texto: str) -> str:
    """Termo digitado pronto para `plainto_tsquery` (todas as palavras são exigidas)."""
    return re.sub(r"\s+", " ", normalizar(texto)).strip()
