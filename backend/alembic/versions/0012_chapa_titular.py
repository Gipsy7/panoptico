"""candidatura.chapa_titular_id: liga vice-presidente, vice-governador e vice-prefeito ao titular

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidatura", sa.Column("chapa_titular_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_candidatura_chapa_titular_id_candidatura"),
        "candidatura",
        "candidatura",
        ["chapa_titular_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_candidatura_chapa_titular_id_candidatura"), "candidatura", type_="foreignkey"
    )
    op.drop_column("candidatura", "chapa_titular_id")
