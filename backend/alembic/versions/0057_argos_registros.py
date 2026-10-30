"""Registros do chat Argos: frases não entendidas, avaliações e conversas consentidas

Só acrescenta três tabelas novas (nada é alterado nem removido). Sem IP, sem user-agent, sem id
de sessão e sem hora exata: só o dia. Sem RECARREGAR_DADOS.

Revision ID: 0057_argos_registros
Revises: 0056_emenda_estadual_chaves
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0057_argos_registros"
down_revision: str | None = "0056_emenda_estadual_chaves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "argos_frase_nao_entendida",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("texto", sa.String(length=300), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
    )
    op.create_index("ix_argos_frase_nao_entendida_dia", "argos_frase_nao_entendida", ["dia"])
    op.create_table(
        "argos_avaliacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("util", sa.Boolean(), nullable=False),
        sa.Column("assunto", sa.String(length=40), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
    )
    op.create_index("ix_argos_avaliacao_dia", "argos_avaliacao", ["dia"])
    op.create_table(
        "argos_conversa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mensagens", postgresql.JSONB(), nullable=False),
        sa.Column("dia", sa.Date(), nullable=False),
    )
    op.create_index("ix_argos_conversa_dia", "argos_conversa", ["dia"])


def downgrade() -> None:
    op.drop_table("argos_conversa")
    op.drop_table("argos_avaliacao")
    op.drop_table("argos_frase_nao_entendida")
