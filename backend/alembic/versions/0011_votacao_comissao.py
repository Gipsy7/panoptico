"""votacao_comissao e voto_comissao: votações nominais nas comissões

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "votacao_comissao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=30), nullable=False),
        sa.Column("orgao_sigla", sa.String(length=30), nullable=False),
        sa.Column("orgao_nome", sa.Text(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("proposicao", sa.String(length=40), nullable=True),
        sa.Column("proposicao_id_externo", sa.String(length=30), nullable=True),
        sa.Column("proposicao_ementa", sa.Text(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_votacao_comissao_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_votacao_comissao")),
        sa.UniqueConstraint("casa", "id_externo", name="uq_votacao_comissao_casa_id_externo"),
    )
    op.create_index("ix_votacao_comissao_casa_data", "votacao_comissao", ["casa", "data"])
    op.create_table(
        "voto_comissao",
        sa.Column("votacao_id", sa.Integer(), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("voto", sa.String(length=60), nullable=False),
        sa.ForeignKeyConstraint(
            ["votacao_id"],
            ["votacao_comissao.id"],
            name=op.f("fk_voto_comissao_votacao_id_votacao_comissao"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_voto_comissao_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("votacao_id", "parlamentar_id", name=op.f("pk_voto_comissao")),
    )
    op.create_index(op.f("ix_voto_comissao_parlamentar_id"), "voto_comissao", ["parlamentar_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_voto_comissao_parlamentar_id"), table_name="voto_comissao")
    op.drop_table("voto_comissao")
    op.drop_index("ix_votacao_comissao_casa_data", table_name="votacao_comissao")
    op.drop_table("votacao_comissao")
