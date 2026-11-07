"""Projetos que viraram lei (Frente 4): normas federais e a ligação com os projetos

Só acrescenta duas tabelas novas (nada é alterado nem removido): `norma` (leis ordinárias, leis
complementares e emendas constitucionais desde 1985, da base de legislação do Senado) e
`norma_proposicao` (que projeto virou cada norma). Carga própria (congresso_normas), sem
RECARREGAR_DADOS.

Revision ID: 0062_normas
Revises: 0061_sugestoes_correcoes
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0062_normas"
down_revision: str | None = "0061_sugestoes_correcoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("norma"):
        return
    op.create_table(
        "norma",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("data_publicacao", sa.Date(), nullable=True),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_norma_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_norma")),
        sa.UniqueConstraint("id_externo", name="uq_norma_id_externo"),
        sa.UniqueConstraint("tipo", "numero", "ano", name="uq_norma_tipo_numero_ano"),
    )
    op.create_index("ix_norma_ano_tipo", "norma", ["ano", "tipo"])
    op.create_table(
        "norma_proposicao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("norma_id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("proposicao_id_externo", sa.String(length=30), nullable=False),
        sa.Column("identificacao", sa.String(length=60), nullable=True),
        sa.Column("origem", sa.String(length=10), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["norma_id"],
            ["norma.id"],
            name=op.f("fk_norma_proposicao_norma_id_norma"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_norma_proposicao_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_norma_proposicao")),
        sa.UniqueConstraint(
            "norma_id", "casa", "proposicao_id_externo", name="uq_norma_proposicao_norma_casa_id"
        ),
    )
    op.create_index(
        op.f("ix_norma_proposicao_norma_id"), "norma_proposicao", ["norma_id"], unique=False
    )
    op.create_index(
        "ix_norma_proposicao_casa_id", "norma_proposicao", ["casa", "proposicao_id_externo"]
    )


def downgrade() -> None:
    op.drop_table("norma_proposicao")
    op.drop_table("norma")
