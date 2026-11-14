"""Alertas de operação enviados por e-mail ao dono: histórico e trava de repetição

Só acrescenta uma tabela nova. Sem dado pessoal: chave do alerta, janela (dia ou hora), assunto,
texto e quando foi enviado. Sem RECARREGAR_DADOS.

Revision ID: 0078_alerta_enviado
Revises: 0077_metrica_diaria
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0078_alerta_enviado"
down_revision: str | None = "0077_metrica_diaria"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerta_enviado",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chave", sa.String(length=40), nullable=False),
        sa.Column("janela", sa.String(length=13), nullable=False),
        sa.Column("assunto", sa.String(length=200), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "enviado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("chave", "janela", name="uq_alerta_enviado_chave_janela"),
    )


def downgrade() -> None:
    op.drop_table("alerta_enviado")
