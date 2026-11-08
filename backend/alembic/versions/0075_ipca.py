"""IPCA mensal do IBGE para valores em reais de hoje (redesenho, onda de dados)

Só acrescenta a tabela `ipca_indice`. Carga própria (ibge_ipca), sem RECARREGAR_DADOS.

Revision ID: 0075_ipca
Revises: 0074_saude_cnes
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0075_ipca"
down_revision: str | None = "0074_saude_cnes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ipca_indice",
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("indice", sa.Numeric(14, 4), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_ipca_indice_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("ano", "mes", name=op.f("pk_ipca_indice")),
    )


def downgrade() -> None:
    op.drop_table("ipca_indice")
