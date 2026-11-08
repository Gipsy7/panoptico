"""IDEB do INEP (redesenho, etapa 5)

Só acrescenta a tabela `ideb_resultado` (nota observada de cada edição por município, estado
e Brasil, etapa e rede). Carga própria (inep_ideb), sem RECARREGAR_DADOS.

Revision ID: 0066_ideb
Revises: 0065_obras_federais
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0066_ideb"
down_revision: str | None = "0065_obras_federais"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ideb_resultado",
        sa.Column("abrangencia", sa.String(length=10), nullable=False),
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("etapa", sa.String(length=10), nullable=False),
        sa.Column("rede", sa.String(length=10), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("valor", sa.Numeric(3, 1), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_ideb_resultado_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint(
            "abrangencia", "codigo", "etapa", "rede", "ano", name=op.f("pk_ideb_resultado")
        ),
    )


def downgrade() -> None:
    op.drop_table("ideb_resultado")
