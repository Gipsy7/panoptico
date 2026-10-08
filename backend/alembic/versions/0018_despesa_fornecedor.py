"""despesa_fornecedor: quanto prefeituras e câmaras pagaram a cada fornecedor (TCEs)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "despesa_fornecedor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("orgao", sa.String(length=20), nullable=False),
        sa.Column("fornecedor", sa.String(length=300), nullable=False),
        sa.Column("documento", sa.String(length=20), nullable=True),
        sa.Column("valor_pago", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("pagamentos", sa.Integer(), nullable=False),
        sa.Column("fonte", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_despesa_fornecedor_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_despesa_fornecedor")),
    )
    op.create_index(
        "ix_despesa_fornecedor_municipio_ano", "despesa_fornecedor", ["municipio_ibge", "ano"]
    )


def downgrade() -> None:
    op.drop_index("ix_despesa_fornecedor_municipio_ano", table_name="despesa_fornecedor")
    op.drop_table("despesa_fornecedor")
