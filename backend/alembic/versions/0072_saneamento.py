"""Saneamento por município no Censo 2022 do IBGE (redesenho, etapa 5)

Só acrescenta a tabela `saneamento_censo` (% de domicílios com água da rede, esgoto na rede e
lixo coletado). Carga própria (ibge_saneamento), sem RECARREGAR_DADOS.

Revision ID: 0072_saneamento
Revises: 0071_internet
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0072_saneamento"
down_revision: str | None = "0071_internet"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saneamento_censo",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("agua_rede", sa.Numeric(5, 2), nullable=True),
        sa.Column("esgoto_rede", sa.Numeric(5, 2), nullable=True),
        sa.Column("lixo_coletado", sa.Numeric(5, 2), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_saneamento_censo_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_saneamento_censo")),
    )


def downgrade() -> None:
    op.drop_table("saneamento_censo")
