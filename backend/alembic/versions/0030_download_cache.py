"""download_cache e conferência da carga em fonte_ingestao

Só aditiva: tabela nova e duas colunas opcionais (total_fonte, alertas).

Revision ID: 0030_download_cache
Revises: 0029_diario_ato
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_download_cache"
down_revision: str | None = "0029_diario_ato"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "download_cache",
        sa.Column("chave", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("etag", sa.String(length=300), nullable=True),
        sa.Column("last_modified", sa.String(length=100), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("tamanho", sa.BigInteger(), nullable=True),
        sa.Column("contexto", sa.String(length=200), nullable=True),
        sa.Column(
            "baixado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("chave"),
    )
    op.add_column("fonte_ingestao", sa.Column("total_fonte", sa.BigInteger(), nullable=True))
    op.add_column("fonte_ingestao", sa.Column("alertas", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("fonte_ingestao", "alertas")
    op.drop_column("fonte_ingestao", "total_fonte")
    op.drop_table("download_cache")
