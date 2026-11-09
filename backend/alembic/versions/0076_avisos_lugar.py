"""Avisos por lugar (cidade, estado, Brasil): assuntos por alvo e frequência por aparelho

Só acrescenta colunas opcionais: `aviso_alvo.assuntos` (JSON; nulo = todos) e
`aviso_inscricao.frequencia` ("dia" ou "semana"; nulo = dia). Sem RECARREGAR_DADOS.

Revision ID: 0076_avisos_lugar
Revises: 0075_ipca
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0076_avisos_lugar"
down_revision: str | None = "0075_ipca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("aviso_alvo", sa.Column("assuntos", sa.JSON(), nullable=True))
    op.add_column("aviso_inscricao", sa.Column("frequencia", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("aviso_inscricao", "frequencia")
    op.drop_column("aviso_alvo", "assuntos")
