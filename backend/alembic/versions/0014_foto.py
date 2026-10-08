"""foto: fotos dos eleitos (TSE) em WebP

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "foto",
        sa.Column("candidatura_id", sa.Integer(), nullable=False),
        sa.Column("webp", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidatura_id"],
            ["candidatura.id"],
            name=op.f("fk_foto_candidatura_id_candidatura"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("candidatura_id", name=op.f("pk_foto")),
    )


def downgrade() -> None:
    op.drop_table("foto")
