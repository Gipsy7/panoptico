"""proposicao e autoria

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposicao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=30), nullable=False),
        sa.Column("sigla_tipo", sa.String(length=10), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.Column("data_apresentacao", sa.Date(), nullable=False),
        sa.Column("situacao", sa.String(length=200), nullable=True),
        sa.Column("virou_lei", sa.Boolean(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_proposicao_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proposicao")),
        sa.UniqueConstraint("casa", "id_externo", name="uq_proposicao_casa_id_externo"),
    )
    op.create_index(op.f("ix_proposicao_data_apresentacao"), "proposicao", ["data_apresentacao"])
    op.create_table(
        "autoria",
        sa.Column("proposicao_id", sa.Integer(), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("primeiro_autor", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_autoria_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposicao_id"],
            ["proposicao.id"],
            name=op.f("fk_autoria_proposicao_id_proposicao"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("proposicao_id", "parlamentar_id", name=op.f("pk_autoria")),
    )
    op.create_index(op.f("ix_autoria_parlamentar_id"), "autoria", ["parlamentar_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_autoria_parlamentar_id"), table_name="autoria")
    op.drop_table("autoria")
    op.drop_index(op.f("ix_proposicao_data_apresentacao"), table_name="proposicao")
    op.drop_table("proposicao")
