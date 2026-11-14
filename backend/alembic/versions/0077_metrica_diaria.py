"""Contagem anônima de acessos: totais por dia, aparelho e origem

Só acrescenta uma tabela nova. Sem IP, sem user-agent, sem identificador e sem hora: só o dia, o
tipo (pagina, visita, entrada, ultima, recurso, busca, uf, cidade, perfil, partido, secao), a
chave, o aparelho (celular ou computador), a categoria de origem e o total. Sem RECARREGAR_DADOS.

Revision ID: 0077_metrica_diaria
Revises: 0076_avisos_lugar
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0077_metrica_diaria"
down_revision: str | None = "0076_avisos_lugar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metrica_diaria",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("aparelho", sa.String(length=10), nullable=False),
        sa.Column("origem", sa.String(length=12), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("dia", "tipo", "chave", "aparelho", "origem"),
    )
    # O painel sempre pergunta "deste tipo, neste intervalo de dias".
    op.create_index("ix_metrica_diaria_tipo_dia", "metrica_diaria", ["tipo", "dia"])


def downgrade() -> None:
    op.drop_index("ix_metrica_diaria_tipo_dia", table_name="metrica_diaria")
    op.drop_table("metrica_diaria")
