"""votacao_local, voto_local e presença em mandato_local (SAPL)

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mandato_local", sa.Column("sessoes", sa.SmallInteger(), nullable=True))
    op.add_column("mandato_local", sa.Column("presencas", sa.SmallInteger(), nullable=True))
    op.create_table(
        "votacao_local",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=12), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("materia", sa.Text(), nullable=False),
        sa.Column("resultado", sa.String(length=60), nullable=True),
        sa.Column("sim", sa.SmallInteger(), nullable=False),
        sa.Column("nao", sa.SmallInteger(), nullable=False),
        sa.Column("abstencoes", sa.SmallInteger(), nullable=False),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_votacao_local_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_votacao_local")),
    )
    op.create_index(
        "ix_votacao_local_casa_uf_municipio", "votacao_local", ["casa", "uf", "municipio_ibge"]
    )
    op.create_table(
        "voto_local",
        sa.Column("votacao_id", sa.Integer(), nullable=False),
        sa.Column("mandato_id", sa.Integer(), nullable=False),
        sa.Column("voto", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["votacao_id"],
            ["votacao_local.id"],
            name=op.f("fk_voto_local_votacao_id_votacao_local"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mandato_id"],
            ["mandato_local.id"],
            name=op.f("fk_voto_local_mandato_id_mandato_local"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("votacao_id", "mandato_id", name=op.f("pk_voto_local")),
    )
    op.create_index("ix_voto_local_mandato", "voto_local", ["mandato_id"])


def downgrade() -> None:
    op.drop_index("ix_voto_local_mandato", table_name="voto_local")
    op.drop_table("voto_local")
    op.drop_index("ix_votacao_local_casa_uf_municipio", table_name="votacao_local")
    op.drop_table("votacao_local")
    op.drop_column("mandato_local", "presencas")
    op.drop_column("mandato_local", "sessoes")
