"""temas das proposições, orientações e proposição votada

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposicao_tema",
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("proposicao_id_externo", sa.String(length=30), nullable=False),
        sa.Column("tema", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint(
            "casa", "proposicao_id_externo", "tema", name=op.f("pk_proposicao_tema")
        ),
    )
    op.create_table(
        "orientacao",
        sa.Column("votacao_id", sa.Integer(), nullable=False),
        sa.Column("bancada", sa.String(length=30), nullable=False),
        sa.Column("orientacao", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["votacao_id"],
            ["votacao.id"],
            name=op.f("fk_orientacao_votacao_id_votacao"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("votacao_id", "bancada", name=op.f("pk_orientacao")),
    )
    op.add_column(
        "votacao", sa.Column("proposicao_id_externo", sa.String(length=30), nullable=True)
    )
    op.add_column("votacao", sa.Column("proposicao_ementa", sa.Text(), nullable=True))
    op.create_index(op.f("ix_votacao_proposicao_id_externo"), "votacao", ["proposicao_id_externo"])
    op.add_column("voto", sa.Column("partido", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("voto", "partido")
    op.drop_index(op.f("ix_votacao_proposicao_id_externo"), table_name="votacao")
    op.drop_column("votacao", "proposicao_ementa")
    op.drop_column("votacao", "proposicao_id_externo")
    op.drop_table("orientacao")
    op.drop_table("proposicao_tema")
