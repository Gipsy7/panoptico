# ruff: noqa: E501  (SQL em linha)
"""Índices da busca por nome (pg_trgm + unaccent), para o `create_all` dos testes.

Em produção quem cria é a migração 0033_busca (o mesmo SQL, escrito à mão). A função
`busca_norm` tira acento, deixa em maiúsculas e troca o que não é letra por espaço: é o
mesmo resultado de `ingestion.comum.chave_nome`, e é IMMUTABLE para poder entrar num índice."""

from sqlalchemy import DDL, Index, event, text

from app.models.base import Base
from app.models.camara_municipal import MandatoLocal
from app.models.candidatura import Candidatura
from app.models.pessoa import Pessoa

PREPARO = (
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    """CREATE OR REPLACE FUNCTION busca_norm(text) RETURNS text
       LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
       AS $$ SELECT regexp_replace(upper(public.unaccent('public.unaccent', $1)), '[^A-Z]', ' ', 'g') $$""",
)  # fmt: skip

for _comando in PREPARO:
    event.listen(Base.metadata, "before_create", DDL(_comando))

ELEITO = text("situacao_turno LIKE 'ELEITO%'")
EM_EXERCICIO = text("em_exercicio")


def _trgm(nome: str, coluna: str, tabela, onde=None) -> Index:
    return Index(
        nome,
        text(f"busca_norm({coluna}) gin_trgm_ops"),
        _table=tabela.__table__,
        postgresql_using="gin",
        postgresql_where=onde,
    )


Index(
    "ix_candidatura_eleito_cargo_ano",
    "cargo",
    "ano_eleicao",
    _table=Candidatura.__table__,
    postgresql_where=ELEITO,
)
_trgm("ix_candidatura_urna_trgm", "nome_urna", Candidatura, ELEITO)
_trgm("ix_candidatura_nome_trgm", "nome", Candidatura, ELEITO)
_trgm("ix_mandato_local_nome_trgm", "nome", MandatoLocal, EM_EXERCICIO)
_trgm("ix_mandato_local_completo_trgm", "nome_completo", MandatoLocal, EM_EXERCICIO)
Index(
    "ix_pessoa_chave_trgm",
    text("chave_nome gin_trgm_ops"),
    _table=Pessoa.__table__,
    postgresql_using="gin",
)
