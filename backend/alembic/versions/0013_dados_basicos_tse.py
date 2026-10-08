"""candidatura: dados pessoais, título e votos; rede_social

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUNAS = [
    ("titulo", sa.String(length=12)),
    ("data_nascimento", sa.Date()),
    ("genero", sa.String(length=40)),
    ("cor_raca", sa.String(length=40)),
    ("grau_instrucao", sa.String(length=60)),
    ("ocupacao", sa.String(length=150)),
    ("estado_civil", sa.String(length=40)),
    ("votos", sa.Integer()),
]


def upgrade() -> None:
    for nome, tipo in COLUNAS:
        op.add_column("candidatura", sa.Column(nome, tipo, nullable=True))
    op.create_index(op.f("ix_candidatura_titulo"), "candidatura", ["titulo"])
    op.create_table(
        "rede_social",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidatura_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidatura_id"],
            ["candidatura.id"],
            name=op.f("fk_rede_social_candidatura_id_candidatura"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rede_social")),
    )
    op.create_index(op.f("ix_rede_social_candidatura_id"), "rede_social", ["candidatura_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_rede_social_candidatura_id"), table_name="rede_social")
    op.drop_table("rede_social")
    op.drop_index(op.f("ix_candidatura_titulo"), table_name="candidatura")
    for nome, _ in reversed(COLUNAS):
        op.drop_column("candidatura", nome)
