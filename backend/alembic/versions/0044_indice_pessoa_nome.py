"""Índice na ordem da busca por nome (docs/DECISOES.md, 2026-10-17)

Só aditiva: índice novo `ix_pessoa_nome`. A busca de pessoas ordena por nome com LIMIT; com um
termo comum ("silva", 10 mil pessoas) o Postgres ordenava todas antes de cortar. Com o índice
lê só as primeiras linhas, no mesmo critério de ordem.

Revision ID: 0044_indice_pessoa_nome
Revises: 0043_indices_de_leitura
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0044_indice_pessoa_nome"
down_revision: str | None = "0043_indices_de_leitura"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_pessoa_nome", "pessoa", ["nome"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_pessoa_nome", table_name="pessoa", if_exists=True)
