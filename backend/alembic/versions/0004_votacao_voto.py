"""votacao, voto e parlamentar.em_exercicio_desde

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("parlamentar", sa.Column("em_exercicio_desde", sa.Date(), nullable=True))
    op.create_table(
        "votacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=30), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("proposicao", sa.String(length=40), nullable=True),
        sa.Column("secreta", sa.Boolean(), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_votacao_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_votacao")),
        sa.UniqueConstraint("casa", "id_externo", name="uq_votacao_casa_id_externo"),
    )
    op.create_index("ix_votacao_casa_data", "votacao", ["casa", "data"])
    op.create_table(
        "voto",
        sa.Column("votacao_id", sa.Integer(), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("voto", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_voto_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["votacao_id"],
            ["votacao.id"],
            name=op.f("fk_voto_votacao_id_votacao"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("votacao_id", "parlamentar_id", name=op.f("pk_voto")),
    )
    op.create_index(op.f("ix_voto_parlamentar_id"), "voto", ["parlamentar_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_voto_parlamentar_id"), table_name="voto")
    op.drop_table("voto")
    op.drop_index("ix_votacao_casa_data", table_name="votacao")
    op.drop_table("votacao")
    op.drop_column("parlamentar", "em_exercicio_desde")
