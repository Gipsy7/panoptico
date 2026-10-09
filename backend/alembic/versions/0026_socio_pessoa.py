"""socio_pessoa e cnpj_consulta: sócios de empresas que aparecem nos dados

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "socio_pessoa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("qualificacao", sa.String(length=80), nullable=True),
        sa.Column("data_entrada", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_socio_pessoa_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_socio_pessoa")),
        sa.UniqueConstraint("pessoa_id", "cnpj", name=op.f("uq_socio_pessoa_pessoa_id")),
    )
    op.create_index(op.f("ix_socio_pessoa_pessoa_id"), "socio_pessoa", ["pessoa_id"])
    op.create_index(op.f("ix_socio_pessoa_cnpj"), "socio_pessoa", ["cnpj"])
    op.create_table(
        "cnpj_consulta",
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("consultado_em", sa.Date(), nullable=False),
        sa.Column("socios", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("cnpj", name=op.f("pk_cnpj_consulta")),
    )


def downgrade() -> None:
    op.drop_table("cnpj_consulta")
    op.drop_table("socio_pessoa")
