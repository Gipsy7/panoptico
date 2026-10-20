"""Agenda pública de agentes federais (e-Agendas, CGU) e contas dos estados (SICONFI)

Só aditiva: `contas_estado` (ingestion/siconfi/contas_estados.py, mesmo formato das contas dos
municípios) e `agenda_compromisso`, carregada por ingestion/executivo/eagendas.py a
partir do arquivo aberto mensal da CGU, só para pessoas da base ligadas por CPF parcial + nome
(ministros, vice-presidente que foi ministro...). Sem RECARREGAR_DADOS: carga própria.

Revision ID: 0048_eagendas
Revises: 0047_emendas_municipio
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0048_eagendas"
down_revision: str | None = "0047_emendas_municipio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("contas_estado"):
        op.create_table(
            "contas_estado",
            sa.Column("uf", sa.String(length=2), nullable=False),
            sa.Column("ano", sa.SmallInteger(), nullable=False),
            sa.Column("populacao", sa.Integer(), nullable=True),
            sa.Column("receita_total", sa.Numeric(16, 2), nullable=True),
            sa.Column("despesa_paga", sa.Numeric(16, 2), nullable=True),
            sa.Column("despesa_por_area", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("uf", "ano", name=op.f("pk_contas_estado")),
        )
    if sa.inspect(op.get_bind()).has_table("agenda_compromisso"):
        return
    op.create_table(
        "agenda_compromisso",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("id_registro", sa.Integer(), nullable=False),
        sa.Column("cargo", sa.String(length=200), nullable=True),
        sa.Column("orgao", sa.String(length=200), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=True),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fim", sa.Time(), nullable=True),
        sa.Column("forma", sa.String(length=20), nullable=True),
        sa.Column("assunto", sa.Text(), nullable=True),
        sa.Column("local", sa.String(length=200), nullable=True),
        sa.Column("origem", sa.String(length=120), nullable=True),
        sa.Column("destino", sa.String(length=120), nullable=True),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.Column("participantes_publicos", postgresql.JSONB(), nullable=True),
        sa.Column("n_participantes_publicos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("entidades_privadas", postgresql.JSONB(), nullable=True),
        sa.Column("n_participantes_privados", sa.Integer(), server_default="0", nullable=False),
        sa.Column("publicado_em", sa.Date(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_agenda_compromisso_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_agenda_compromisso_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agenda_compromisso")),
        sa.UniqueConstraint(
            "pessoa_id", "tipo", "id_registro", name=op.f("uq_agenda_compromisso_pessoa_id")
        ),
    )
    op.create_index(
        "ix_agenda_compromisso_pessoa_data", "agenda_compromisso", ["pessoa_id", "data_inicio"]
    )


def downgrade() -> None:
    op.drop_index("ix_agenda_compromisso_pessoa_data", table_name="agenda_compromisso")
    op.drop_table("agenda_compromisso")
    op.drop_table("contas_estado")
