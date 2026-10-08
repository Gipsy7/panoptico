"""gasto_local: gastos do gabinete de parlamentares estaduais (verba indenizatória)

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gasto_local",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mandato_id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("categoria", sa.String(length=200), nullable=False),
        sa.Column("valor", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["mandato_id"],
            ["mandato_local.id"],
            name=op.f("fk_gasto_local_mandato_id_mandato_local"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gasto_local")),
    )
    op.create_index("ix_gasto_local_mandato_ano", "gasto_local", ["mandato_id", "ano"])


def downgrade() -> None:
    op.drop_index("ix_gasto_local_mandato_ano", table_name="gasto_local")
    op.drop_table("gasto_local")
