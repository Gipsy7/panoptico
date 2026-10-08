"""canal_oficial: sites oficiais dos municípios (catálogo da varredura)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canal_oficial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sistema", sa.String(length=40), nullable=True),
        sa.Column("verificado_em", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_canal_oficial_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canal_oficial")),
    )
    op.create_index(op.f("ix_canal_oficial_municipio_ibge"), "canal_oficial", ["municipio_ibge"])


def downgrade() -> None:
    op.drop_index(op.f("ix_canal_oficial_municipio_ibge"), table_name="canal_oficial")
    op.drop_table("canal_oficial")
