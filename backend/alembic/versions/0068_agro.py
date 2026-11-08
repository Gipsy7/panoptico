"""Produção Agrícola Municipal do IBGE (redesenho, etapa 5)

Só acrescenta a tabela `agro_lavoura` (valor da produção por produto, município, estado e
Brasil). Carga própria (ibge_pam), sem RECARREGAR_DADOS.

Revision ID: 0068_agro
Revises: 0067_pib
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0068_agro"
down_revision: str | None = "0067_pib"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agro_lavoura",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("produto", sa.String(length=80), nullable=False),
        sa.Column("valor", sa.Numeric(16, 0), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_agro_lavoura_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", "ano", "produto", name=op.f("pk_agro_lavoura")),
    )


def downgrade() -> None:
    op.drop_table("agro_lavoura")
