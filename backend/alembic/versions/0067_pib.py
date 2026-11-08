"""PIB dos Municípios do IBGE (redesenho, etapa 5)

Só acrescenta a tabela `pib_ibge` (PIB e valor adicionado por atividade, por município, estado
e Brasil, desde 2002). Carga própria (ibge_pib), sem RECARREGAR_DADOS.

Revision ID: 0067_pib
Revises: 0066_ideb
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0067_pib"
down_revision: str | None = "0066_ideb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pib_ibge",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("pib", sa.Numeric(16, 0), nullable=False),
        sa.Column("vab_total", sa.Numeric(16, 0), nullable=True),
        sa.Column("vab_agropecuaria", sa.Numeric(16, 0), nullable=True),
        sa.Column("vab_industria", sa.Numeric(16, 0), nullable=True),
        sa.Column("vab_servicos", sa.Numeric(16, 0), nullable=True),
        sa.Column("vab_administracao", sa.Numeric(16, 0), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_pib_ibge_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", "ano", name=op.f("pk_pib_ibge")),
    )


def downgrade() -> None:
    op.drop_table("pib_ibge")
