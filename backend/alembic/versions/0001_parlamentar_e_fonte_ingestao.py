"""parlamentar e fonte_ingestao

Revision ID: 0001
Revises:
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fonte_ingestao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fonte", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("arquivo_raw", sa.String(length=500), nullable=False),
        sa.Column(
            "iniciado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registros", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fonte_ingestao")),
    )
    op.create_index(op.f("ix_fonte_ingestao_fonte"), "fonte_ingestao", ["fonte"])

    op.create_table(
        "parlamentar",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("nome_parlamentar", sa.String(length=200), nullable=False),
        sa.Column("nome_civil", sa.String(length=200), nullable=True),
        sa.Column("partido", sa.String(length=30), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("foto_url", sa.String(length=500), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("telefone", sa.String(length=100), nullable=True),
        sa.Column("pagina_url", sa.String(length=500), nullable=True),
        sa.Column("em_exercicio", sa.Boolean(), nullable=False),
        sa.Column("fonte_url", sa.String(length=500), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_parlamentar_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parlamentar")),
        sa.UniqueConstraint("casa", "id_externo", name="uq_parlamentar_casa_id_externo"),
    )
    op.create_index(op.f("ix_parlamentar_uf"), "parlamentar", ["uf"])


def downgrade() -> None:
    op.drop_index(op.f("ix_parlamentar_uf"), table_name="parlamentar")
    op.drop_table("parlamentar")
    op.drop_index(op.f("ix_fonte_ingestao_fonte"), table_name="fonte_ingestao")
    op.drop_table("fonte_ingestao")
