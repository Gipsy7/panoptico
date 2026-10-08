"""candidatura: índices para vereadores por município e deputados estaduais por UF

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_candidatura_municipio_ibge", "candidatura", ["municipio_ibge"])
    op.create_index("ix_candidatura_cargo_uf", "candidatura", ["cargo", "uf"])


def downgrade() -> None:
    op.drop_index("ix_candidatura_cargo_uf", table_name="candidatura")
    op.drop_index("ix_candidatura_municipio_ibge", table_name="candidatura")
