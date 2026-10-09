"""caso e caso_documento (curadoria de casos com documentos oficiais) e evento.caso_slug

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "caso",
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("periodo", sa.String(length=40), nullable=True),
        sa.Column("resumo", sa.Text(), nullable=False),
        sa.Column("conferido_em", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("slug", name=op.f("pk_caso")),
    )
    op.create_table(
        "caso_documento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("caso_slug", sa.String(length=60), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("orgao", sa.String(length=120), nullable=False),
        sa.Column("numero", sa.String(length=60), nullable=True),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("resumo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["caso_slug"],
            ["caso.slug"],
            name=op.f("fk_caso_documento_caso_slug_caso"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_caso_documento")),
        sa.UniqueConstraint("caso_slug", "codigo", name=op.f("uq_caso_documento_caso_slug")),
    )
    op.add_column("evento", sa.Column("caso_slug", sa.String(length=60), nullable=True))
    op.create_foreign_key(
        op.f("fk_evento_caso_slug_caso"),
        "evento",
        "caso",
        ["caso_slug"],
        ["slug"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_evento_caso_slug"), "evento", ["caso_slug"])


def downgrade() -> None:
    op.drop_index(op.f("ix_evento_caso_slug"), table_name="evento")
    op.drop_constraint(op.f("fk_evento_caso_slug_caso"), "evento", type_="foreignkey")
    op.drop_column("evento", "caso_slug")
    op.drop_table("caso_documento")
    op.drop_table("caso")
