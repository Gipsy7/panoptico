"""Medidas provisórias e vetos do Presidente da República (tabela nova)

Só aditiva: `ato_presidencial`, carga própria (`congresso_atos_presidente`); sem
RECARREGAR_DADOS. Nota para o coordenador: se outra branch também criou a 0057, renumere.

Revision ID: 0057_ato_presidencial
Revises: 0056_emenda_estadual_chaves
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0057_ato_presidencial"
down_revision: str | None = "0056_emenda_estadual_chaves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("ato_presidencial"):
        return
    op.create_table(
        "ato_presidencial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("identificacao", sa.String(length=30), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.Column("apelido", sa.Text(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("data_decisao", sa.Date(), nullable=True),
        sa.Column("situacao", sa.String(length=200), nullable=True),
        sa.Column("decisao", sa.String(length=40), nullable=True),
        sa.Column("tramitando", sa.Boolean(), nullable=False),
        sa.Column("veto_total", sa.Boolean(), nullable=True),
        sa.Column("norma_gerada", sa.String(length=200), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_ato_presidencial_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ato_presidencial")),
        sa.UniqueConstraint("tipo", "id_externo", name="uq_ato_presidencial_tipo_id_externo"),
    )
    op.create_index("ix_ato_presidencial_tipo_data", "ato_presidencial", ["tipo", "data"])


def downgrade() -> None:
    op.drop_table("ato_presidencial")
