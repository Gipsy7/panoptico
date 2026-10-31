"""Contagem anônima de acessos: totais por dia

Só acrescenta uma tabela nova. Sem IP, sem user-agent, sem identificador e sem hora: só o dia, o
tipo (pagina, visita, origem, dispositivo, recurso), a chave e o total. Sem RECARREGAR_DADOS.

Revision ID: 0059_metrica_diaria
Revises: 0058_avisos_web_push
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0059_metrica_diaria"
down_revision: str | None = "0058_avisos_web_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metrica_diaria",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("dia", "tipo", "chave"),
    )


def downgrade() -> None:
    op.drop_table("metrica_diaria")
