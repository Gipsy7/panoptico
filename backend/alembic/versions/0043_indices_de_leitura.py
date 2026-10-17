"""Dois índices de leitura achados na medição das rotas (docs/DECISOES.md, 2026-10-17)

Só aditiva: índices novos, nenhum dado muda e nenhum índice sai.
- `ix_candidatura_chapa_titular`: o vice (e os vices de chapa) são buscados pelo titular em
  /executivo e /estados/{uf}/eleitos-2026; sem índice era uma varredura da tabela por consulta.
- `ix_despesa_casa_ano_mes`: `max(mes)` do ano em /parlamentares/{id}/gastos lia a tabela toda
  da Casa; com o mês no índice vira leitura só do índice.

Revision ID: 0043_indices_de_leitura
Revises: 0042_emenda_relator
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0043_indices_de_leitura"
down_revision: str | None = "0042_emenda_relator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_candidatura_chapa_titular",
        "candidatura",
        ["chapa_titular_id"],
        postgresql_where=sa.text("chapa_titular_id IS NOT NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_despesa_casa_ano_mes", "despesa", ["casa", "ano", "mes"], if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index("ix_despesa_casa_ano_mes", table_name="despesa", if_exists=True)
    op.drop_index("ix_candidatura_chapa_titular", table_name="candidatura", if_exists=True)
