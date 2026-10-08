"""contas_municipio: contas anuais dos municípios (SICONFI)

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contas_municipio",
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("populacao", sa.Integer(), nullable=True),
        sa.Column("receita_total", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("despesa_paga", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("despesa_por_area", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_contas_municipio_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("municipio_ibge", "ano", name=op.f("pk_contas_municipio")),
    )


def downgrade() -> None:
    op.drop_table("contas_municipio")
