"""emenda parlamentar

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emenda",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=100), nullable=False),
        sa.Column("individual", sa.Boolean(), nullable=False),
        sa.Column("autor_codigo", sa.String(length=20), nullable=False),
        sa.Column("autor_nome", sa.String(length=200), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=True),
        sa.Column("localidade", sa.String(length=200), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("uf", sa.String(length=50), nullable=True),
        sa.Column("funcao", sa.String(length=100), nullable=True),
        sa.Column("acao", sa.String(length=300), nullable=True),
        sa.Column("valor_empenhado", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_ingestao_id_fonte_ingestao"),
        ),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_emenda_parlamentar_id_parlamentar"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda")),
    )
    op.create_index("ix_emenda_codigo", "emenda", ["codigo"])
    op.create_index("ix_emenda_municipio_ano", "emenda", ["municipio_ibge", "ano"])
    op.create_index("ix_emenda_parlamentar_ano", "emenda", ["parlamentar_id", "ano"])


def downgrade() -> None:
    op.drop_index("ix_emenda_parlamentar_ano", table_name="emenda")
    op.drop_index("ix_emenda_municipio_ano", table_name="emenda")
    op.drop_index("ix_emenda_codigo", table_name="emenda")
    op.drop_table("emenda")
