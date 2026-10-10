"""Busca por nome: pg_trgm + unaccent e índices GIN de trigramas

Só aditiva (extensões, uma função e índices). `busca_norm` é o `chave_nome` do Python em SQL
IMMUTABLE. Os índices de candidatura e mandato_local são parciais (só eleitos e quem está
no cargo), que é o único conjunto que a busca consulta. pg_trgm e unaccent são extensões
suportadas pelo Neon.

Revision ID: 0033_busca
Revises: 0032_dou
Create Date: 2026-10-10
"""

# ruff: noqa: E501  (SQL em linha)

from collections.abc import Sequence

from alembic import op

revision: str = "0033_busca"
down_revision: str | None = "0032_dou"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICES = (
    ("ix_candidatura_urna_trgm", "candidatura", "busca_norm(nome_urna)", "situacao_turno LIKE 'ELEITO%'"),
    ("ix_candidatura_nome_trgm", "candidatura", "busca_norm(nome)", "situacao_turno LIKE 'ELEITO%'"),
    ("ix_mandato_local_nome_trgm", "mandato_local", "busca_norm(nome)", "em_exercicio"),
    ("ix_mandato_local_completo_trgm", "mandato_local", "busca_norm(nome_completo)", "em_exercicio"),
    ("ix_pessoa_chave_trgm", "pessoa", "chave_nome", None),
)  # fmt: skip


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """CREATE OR REPLACE FUNCTION busca_norm(text) RETURNS text
           LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
           AS $$ SELECT regexp_replace(upper(public.unaccent('public.unaccent', $1)), '[^A-Z]', ' ', 'g') $$"""
    )
    # Eleição mais recente por cargo, sem varrer a tabela (busca de eleitos).
    op.execute(
        "CREATE INDEX ix_candidatura_eleito_cargo_ano ON candidatura (cargo, ano_eleicao) "
        "WHERE situacao_turno LIKE 'ELEITO%'"
    )
    for nome, tabela, expressao, onde in INDICES:
        filtro = f" WHERE {onde}" if onde else ""
        op.execute(f"CREATE INDEX {nome} ON {tabela} USING gin ({expressao} gin_trgm_ops){filtro}")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_candidatura_eleito_cargo_ano")
    for nome, *_ in INDICES:
        op.execute(f"DROP INDEX IF EXISTS {nome}")
    op.execute("DROP FUNCTION IF EXISTS busca_norm(text)")
