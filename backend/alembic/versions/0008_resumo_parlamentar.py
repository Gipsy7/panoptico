"""resumo_parlamentar

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resumo_parlamentar",
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("gastos", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("presenca_votou", sa.Integer(), nullable=False),
        sa.Column("presenca_total", sa.Integer(), nullable=False),
        sa.Column("governo_iguais", sa.Integer(), nullable=False),
        sa.Column("governo_total", sa.Integer(), nullable=False),
        sa.Column("partido_iguais", sa.Integer(), nullable=False),
        sa.Column("partido_total", sa.Integer(), nullable=False),
        sa.Column("projetos", sa.Integer(), nullable=False),
        sa.Column("homenagens", sa.Integer(), nullable=False),
        sa.Column("normas", sa.Integer(), nullable=False),
        sa.Column("emendas_pagas", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_resumo_parlamentar_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("parlamentar_id", "ano", name=op.f("pk_resumo_parlamentar")),
    )


def downgrade() -> None:
    op.drop_table("resumo_parlamentar")
