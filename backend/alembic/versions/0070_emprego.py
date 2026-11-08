"""Cadastro Central de Empresas do IBGE (redesenho, etapa 5)

Só acrescenta as tabelas `emprego_ibge` (empresas, pessoas ocupadas, assalariados e salário
médio por ano) e `emprego_setor` (pessoas ocupadas por seção da CNAE). Carga própria
(ibge_cempre), sem RECARREGAR_DADOS.

Revision ID: 0070_emprego
Revises: 0069_pecuaria
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0070_emprego"
down_revision: str | None = "0069_pecuaria"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emprego_ibge",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("empresas", sa.Numeric(12, 0), nullable=True),
        sa.Column("pessoal_ocupado", sa.Numeric(12, 0), nullable=False),
        sa.Column("assalariados", sa.Numeric(12, 0), nullable=True),
        sa.Column("salario_medio", sa.Numeric(12, 2), nullable=True),
        sa.Column("salario_medio_sm", sa.Numeric(6, 2), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emprego_ibge_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", "ano", name=op.f("pk_emprego_ibge")),
    )
    op.create_table(
        "emprego_setor",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("secao", sa.String(length=1), nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("pessoal_ocupado", sa.Numeric(12, 0), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emprego_setor_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("codigo", "ano", "secao", name=op.f("pk_emprego_setor")),
    )


def downgrade() -> None:
    op.drop_table("emprego_setor")
    op.drop_table("emprego_ibge")
