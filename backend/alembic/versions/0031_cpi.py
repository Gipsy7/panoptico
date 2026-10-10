"""cpi, cpi_participacao e cpi_indiciamento_sugestao: CPIs e CPMIs desde 2019

Só aditiva. Nada em cpi_indiciamento_sugestao é publicável: `revisado` nasce falso.

Revision ID: 0031_cpi
Revises: 0030_download_cache
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_cpi"
down_revision: str | None = "0030_download_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cpi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=12), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("tipo", sa.String(length=5), nullable=False),
        sa.Column("sigla", sa.String(length=60), nullable=True),
        sa.Column("nome", sa.String(length=300), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("data_criacao", sa.Date(), nullable=True),
        sa.Column("data_instalacao", sa.Date(), nullable=True),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("situacao", sa.String(length=80), nullable=True),
        sa.Column("relatorio_url", sa.Text(), nullable=True),
        sa.Column("relatorio_rotulo", sa.String(length=200), nullable=True),
        sa.Column("fonte_url", sa.Text(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"], ["fonte_ingestao.id"], name=op.f("fk_cpi_ingestao_id_fonte_ingestao")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpi")),
        sa.UniqueConstraint("casa", "id_externo", name=op.f("uq_cpi_casa")),
    )
    op.create_table(
        "cpi_participacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cpi_id", sa.Integer(), nullable=False),
        sa.Column("casa_parlamentar", sa.String(length=10), nullable=False),
        sa.Column("id_parlamentar", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("cargo", sa.String(length=30), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("pessoa_id", sa.Integer(), nullable=True),
        sa.Column("regra", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(
            ["cpi_id"], ["cpi.id"], name=op.f("fk_cpi_participacao_cpi_id_cpi"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_cpi_participacao_pessoa_id_pessoa"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpi_participacao")),
    )
    op.create_index(op.f("ix_cpi_participacao_cpi_id"), "cpi_participacao", ["cpi_id"])
    op.create_index(op.f("ix_cpi_participacao_pessoa_id"), "cpi_participacao", ["pessoa_id"])
    op.create_table(
        "cpi_indiciamento_sugestao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cpi_id", sa.Integer(), nullable=False),
        sa.Column("nome_citado", sa.String(length=200), nullable=False),
        sa.Column("pessoa_juridica", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("trecho", sa.Text(), nullable=False),
        sa.Column("pagina", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("revisado", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["cpi_id"],
            ["cpi.id"],
            name=op.f("fk_cpi_indiciamento_sugestao_cpi_id_cpi"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpi_indiciamento_sugestao")),
        sa.UniqueConstraint(
            "cpi_id", "nome_citado", name=op.f("uq_cpi_indiciamento_sugestao_cpi_id")
        ),
    )
    op.create_index(
        op.f("ix_cpi_indiciamento_sugestao_cpi_id"), "cpi_indiciamento_sugestao", ["cpi_id"]
    )


def downgrade() -> None:
    op.drop_table("cpi_indiciamento_sugestao")
    op.drop_table("cpi_participacao")
    op.drop_table("cpi")
