"""processo: situação no DataJud (CNJ) dos processos citados nos eventos

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processo",
        sa.Column("numero", sa.String(length=25), nullable=False),
        sa.Column("tribunal", sa.String(length=12), nullable=True),
        sa.Column("classe", sa.String(length=150), nullable=True),
        sa.Column("orgao_julgador", sa.String(length=200), nullable=True),
        sa.Column("data_ajuizamento", sa.Date(), nullable=True),
        sa.Column("ultimo_andamento", sa.String(length=200), nullable=True),
        sa.Column("data_ultimo_andamento", sa.Date(), nullable=True),
        sa.Column("sigiloso", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("encontrado", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("consultado_em", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("numero", name=op.f("pk_processo")),
    )


def downgrade() -> None:
    op.drop_table("processo")
