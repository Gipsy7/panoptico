"""PNCP na produção: soma anual por município × fornecedor e a janela dos últimos dias

Só aditiva: duas tabelas novas e uma coluna com valor padrão em pncp_dia. O acervo local
continua usando pncp_soma (por dia); a produção usa pncp_janela (poucos dias, para reler sem
somar duas vezes) e pncp_anual (o que o site mostra).

Revision ID: 0034_pncp_anual
Revises: 0033_busca
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_pncp_anual"
down_revision: str | None = "0033_busca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pncp_dia",
        sa.Column("compactado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "pncp_janela",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=False),
        sa.Column("fornecedor_nome", sa.String(length=120), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_global", sa.Numeric(18, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "dia", "municipio_ibge", "fornecedor_cnpj", name=op.f("pk_pncp_janela")
        ),
    )
    op.create_table(
        "pncp_anual",
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=False),
        sa.Column("fornecedor_nome", sa.String(length=120), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_global", sa.Numeric(18, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "ano", "municipio_ibge", "fornecedor_cnpj", name=op.f("pk_pncp_anual")
        ),
    )
    op.create_index("ix_pncp_anual_municipio", "pncp_anual", ["municipio_ibge", "ano"])


def downgrade() -> None:
    op.drop_index("ix_pncp_anual_municipio", table_name="pncp_anual")
    op.drop_table("pncp_anual")
    op.drop_table("pncp_janela")
    op.drop_column("pncp_dia", "compactado")
