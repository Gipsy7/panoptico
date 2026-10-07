"""despesa (cota parlamentar)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "despesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("categoria", sa.String(length=300), nullable=False),
        sa.Column("fornecedor", sa.String(length=300), nullable=True),
        sa.Column("cnpj_cpf", sa.String(length=30), nullable=True),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("url_documento", sa.String(length=500), nullable=True),
        sa.Column("id_externo", sa.String(length=30), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_despesa_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_despesa_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_despesa")),
    )
    op.create_index("ix_despesa_parlamentar_ano", "despesa", ["parlamentar_id", "ano"])
    op.create_index("ix_despesa_casa_ano", "despesa", ["casa", "ano"])


def downgrade() -> None:
    op.drop_index("ix_despesa_casa_ano", table_name="despesa")
    op.drop_index("ix_despesa_parlamentar_ano", table_name="despesa")
    op.drop_table("despesa")
