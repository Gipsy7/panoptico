"""sancao_empresa: sanções da CGU a empresas que aparecem como fornecedores

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sancao_empresa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cadastro", sa.String(length=10), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("nome", sa.String(length=300), nullable=False),
        sa.Column("categoria", sa.String(length=200), nullable=False),
        sa.Column("abrangencia", sa.String(length=120), nullable=True),
        sa.Column("orgao", sa.String(length=300), nullable=True),
        sa.Column("inicio", sa.Date(), nullable=True),
        sa.Column("fim", sa.Date(), nullable=True),
        sa.Column("processo", sa.String(length=40), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sancao_empresa")),
        sa.UniqueConstraint("cadastro", "codigo", name=op.f("uq_sancao_empresa_cadastro")),
    )
    op.create_index(op.f("ix_sancao_empresa_cnpj"), "sancao_empresa", ["cnpj"])


def downgrade() -> None:
    op.drop_table("sancao_empresa")
