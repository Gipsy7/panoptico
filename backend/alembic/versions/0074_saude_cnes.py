"""Saúde por município no CNES do DATASUS (redesenho, etapa 5)

Só acrescenta a tabela `saude_cnes` (leitos, unidades básicas e hospitais no mês mais recente).
Carga própria (datasus_cnes), sem RECARREGAR_DADOS.

Revision ID: 0074_saude_cnes
Revises: 0073_homicidios
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0074_saude_cnes"
down_revision: str | None = "0073_homicidios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saude_cnes",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("leitos", sa.Integer(), nullable=False),
        sa.Column("leitos_sus", sa.Integer(), nullable=False),
        sa.Column("leitos_complementares", sa.Integer(), nullable=False),
        sa.Column("leitos_complementares_sus", sa.Integer(), nullable=False),
        sa.Column("ubs", sa.Integer(), nullable=False),
        sa.Column("hospitais", sa.Integer(), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_saude_cnes_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_saude_cnes")),
    )


def downgrade() -> None:
    op.drop_table("saude_cnes")
