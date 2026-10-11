"""PNCP: CNPJs de órgãos públicos, para rotular repasses entre órgãos no ranking de fornecedores

Só aditiva: tabela `pncp_ente_publico`. Na produção `pncp_orgao` não é gravado; esta guarda só
o CNPJ (o pacote histórico e o diário a preenchem).

Revision ID: 0036_pncp_ente_publico
Revises: 0035_pncp_suspeito
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_pncp_ente_publico"
down_revision: str | None = "0035_pncp_suspeito"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pncp_ente_publico",
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.PrimaryKeyConstraint("cnpj", name=op.f("pk_pncp_ente_publico")),
    )
    # onde pncp_orgao existe (acervo, desenvolvimento), aproveita
    op.execute("INSERT INTO pncp_ente_publico SELECT cnpj FROM pncp_orgao ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table("pncp_ente_publico")
