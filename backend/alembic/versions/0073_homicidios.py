"""Homicídios por município no SIM do DATASUS (redesenho, etapa 5)

Só acrescenta a tabela `homicidio_sim` (contagem por lugar de residência e ano). Carga própria
(datasus_homicidios), sem RECARREGAR_DADOS.

Revision ID: 0073_homicidios
Revises: 0072_saneamento
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0073_homicidios"
down_revision: str | None = "0072_saneamento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "homicidio_sim",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("homicidios", sa.Integer(), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_homicidio_sim_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", "ano", name=op.f("pk_homicidio_sim")),
    )


def downgrade() -> None:
    op.drop_table("homicidio_sim")
