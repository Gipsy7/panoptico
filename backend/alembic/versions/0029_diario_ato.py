"""diario_ato e diario_consulta: sugestões de atos de pessoal achados nos diários oficiais

Só aditiva. Nada aqui é publicável: `revisado` nasce falso.

Revision ID: 0029_diario_ato
Revises: 0028_pncp
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_diario_ato"
down_revision: str | None = "0028_pncp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diario_ato",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo_ato", sa.String(length=20), nullable=False),
        sa.Column("trecho", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("revisado", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_diario_ato_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diario_ato")),
        sa.UniqueConstraint("pessoa_id", "url", name=op.f("uq_diario_ato_pessoa_id")),
    )
    op.create_index(op.f("ix_diario_ato_pessoa_id"), "diario_ato", ["pessoa_id"])
    op.create_index(op.f("ix_diario_ato_municipio_ibge"), "diario_ato", ["municipio_ibge"])
    op.create_table(
        "diario_consulta",
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("consultado_em", sa.Date(), nullable=False),
        sa.Column("achados", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_diario_consulta_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pessoa_id", "municipio_ibge", name=op.f("pk_diario_consulta")),
    )


def downgrade() -> None:
    op.drop_table("diario_consulta")
    op.drop_table("diario_ato")
