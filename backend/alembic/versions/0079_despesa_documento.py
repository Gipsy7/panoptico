"""Índice pelo documento do fornecedor nas despesas de gabinete (ficha do fornecedor)

Só acrescenta um índice: os 14 dígitos do documento, sem pontuação, a mesma expressão que
app/services/ficha_fornecedor.py usa para achar os pagamentos de um CNPJ. Sem ele, cada ficha
varre a tabela inteira. Sem RECARREGAR_DADOS.

Revision ID: 0079_despesa_documento
Revises: 0078_alerta_enviado
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0079_despesa_documento"
down_revision: str | None = "0078_alerta_enviado"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_despesa_documento",
        "despesa",
        [sa.text(r"regexp_replace(coalesce(cnpj_cpf, ''), '\D', '', 'g')")],
    )


def downgrade() -> None:
    op.drop_index("ix_despesa_documento", table_name="despesa")
