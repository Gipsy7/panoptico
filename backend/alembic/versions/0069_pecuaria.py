"""Pesquisa da Pecuária Municipal do IBGE (redesenho, etapa 5)

Só acrescenta a tabela `agro_pecuaria` (rebanhos e produção de origem animal por município,
estado e Brasil). Carga própria (ibge_ppm), sem RECARREGAR_DADOS.

Revision ID: 0069_pecuaria
Revises: 0068_agro
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0069_pecuaria"
down_revision: str | None = "0068_agro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agro_pecuaria",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("categoria", sa.String(length=10), nullable=False),
        sa.Column("item", sa.String(length=80), nullable=False),
        sa.Column("valor", sa.Numeric(16, 0), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_agro_pecuaria_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint(
            "codigo", "ano", "categoria", "item", name=op.f("pk_agro_pecuaria")
        ),
    )


def downgrade() -> None:
    op.drop_table("agro_pecuaria")
