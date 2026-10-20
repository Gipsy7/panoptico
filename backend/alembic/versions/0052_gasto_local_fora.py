"""Gastos do gabinete que a planilha traz mas ficam fora da soma por mês

Só aditiva: `gasto_local_fora`, por mandato e ano (hoje preenchida pela CLDF: comprovantes sem
data). Sem RECARREGAR_DADOS: a próxima carga da CLDF preenche.

Revision ID: 0052_gasto_local_fora
Revises: 0051_dinheiro_federal
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0052_gasto_local_fora"
down_revision: str | None = "0051_dinheiro_federal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("gasto_local_fora"):
        return
    op.create_table(
        "gasto_local_fora",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mandato_id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("linhas", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("linhas_valor_ilegivel", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["mandato_id"],
            ["mandato_local.id"],
            name=op.f("fk_gasto_local_fora_mandato_id_mandato_local"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gasto_local_fora")),
    )
    op.create_index("ix_gasto_local_fora_mandato", "gasto_local_fora", ["mandato_id"])


def downgrade() -> None:
    op.drop_table("gasto_local_fora")
