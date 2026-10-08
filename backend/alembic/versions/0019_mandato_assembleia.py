"""mandato_local também para assembleias legislativas (SAPL): casa e uf

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mandato_local",
        sa.Column("casa", sa.String(length=12), server_default="camara", nullable=False),
    )
    op.add_column("mandato_local", sa.Column("uf", sa.String(length=2), nullable=True))
    op.execute(
        "UPDATE mandato_local m SET uf = mu.uf FROM municipio mu WHERE mu.ibge = m.municipio_ibge"
    )
    op.alter_column("mandato_local", "uf", nullable=False)
    op.alter_column("mandato_local", "municipio_ibge", nullable=True)
    op.alter_column("projeto_local", "municipio_ibge", nullable=True)
    op.create_index("ix_mandato_local_casa_uf", "mandato_local", ["casa", "uf"])


def downgrade() -> None:
    op.drop_index("ix_mandato_local_casa_uf", table_name="mandato_local")
    op.execute("DELETE FROM mandato_local WHERE municipio_ibge IS NULL")
    op.alter_column("projeto_local", "municipio_ibge", nullable=False)
    op.alter_column("mandato_local", "municipio_ibge", nullable=False)
    op.drop_column("mandato_local", "uf")
    op.drop_column("mandato_local", "casa")
