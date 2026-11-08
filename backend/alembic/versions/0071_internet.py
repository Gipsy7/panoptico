"""Banda larga fixa da Anatel por município (redesenho, etapa 5)

Só acrescenta a tabela `internet_fixa` (acessos do mês mais recente, de fibra e de mais de 34
Mbps, por município). Carga própria (anatel_banda_larga), sem RECARREGAR_DADOS.

Revision ID: 0071_internet
Revises: 0070_emprego
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0071_internet"
down_revision: str | None = "0070_emprego"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "internet_fixa",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("acessos", sa.Integer(), nullable=False),
        sa.Column("acessos_fibra", sa.Integer(), nullable=False),
        sa.Column("acessos_rapidos", sa.Integer(), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_internet_fixa_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_internet_fixa")),
    )


def downgrade() -> None:
    op.drop_table("internet_fixa")
