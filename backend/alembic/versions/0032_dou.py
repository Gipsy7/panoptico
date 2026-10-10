"""dou_ato: sugestões de atos de pessoal achados por nome na Seção 2 do DOU

Só aditiva. Nada aqui é publicável: `revisado` nasce falso.

Revision ID: 0032_dou
Revises: 0031_cpi
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_dou"
down_revision: str | None = "0031_cpi"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dou_ato",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("id_materia", sa.String(length=20), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("tipo_ato", sa.String(length=20), nullable=False),
        sa.Column("orgao", sa.Text(), nullable=False),
        sa.Column("tipo_materia", sa.String(length=100), nullable=True),
        sa.Column("trecho", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("revisado", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_dou_ato_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dou_ato")),
        sa.UniqueConstraint("pessoa_id", "id_materia", name=op.f("uq_dou_ato_pessoa_id")),
    )
    op.create_index(op.f("ix_dou_ato_pessoa_id"), "dou_ato", ["pessoa_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_dou_ato_pessoa_id"), table_name="dou_ato")
    op.drop_table("dou_ato")
