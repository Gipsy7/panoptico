"""pncp_soma, pncp_contrato, pncp_orgao e pncp_dia: contratos do PNCP (coleta mínima)

Só aditiva.

Revision ID: 0028_pncp
Revises: 0027_contas_partidarias
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028_pncp"
down_revision: str | None = "0027_contas_partidarias"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pncp_soma",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("orgao_cnpj", sa.String(length=14), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("tipo_pessoa", sa.String(length=2), nullable=False),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=False),
        sa.Column("tipo_contrato", sa.String(length=60), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_global", sa.Numeric(18, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "dia",
            "orgao_cnpj",
            "municipio_ibge",
            "tipo_pessoa",
            "fornecedor_cnpj",
            "tipo_contrato",
            name=op.f("pk_pncp_soma"),
        ),
    )
    op.create_index("ix_pncp_soma_fornecedor_cnpj", "pncp_soma", ["fornecedor_cnpj"])
    op.create_table(
        "pncp_contrato",
        sa.Column("numero_controle", sa.String(length=40), nullable=False),
        sa.Column("orgao_cnpj", sa.String(length=14), nullable=False),
        sa.Column("orgao_nome", sa.String(length=300), nullable=True),
        sa.Column("esfera", sa.String(length=1), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("municipio_nome", sa.String(length=120), nullable=True),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=False),
        sa.Column("fornecedor_nome", sa.String(length=300), nullable=True),
        sa.Column("tipo_contrato", sa.String(length=60), nullable=False),
        sa.Column("categoria", sa.String(length=60), nullable=True),
        sa.Column("receita", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("valor_inicial", sa.Numeric(18, 2), nullable=True),
        sa.Column("valor_global", sa.Numeric(18, 2), nullable=True),
        sa.Column("valor_acumulado", sa.Numeric(18, 2), nullable=True),
        sa.Column("data_assinatura", sa.Date(), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("publicado_em", sa.Date(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=True),
        sa.Column("compra_pncp", sa.String(length=40), nullable=True),
        sa.Column("processo", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("numero_controle", name=op.f("pk_pncp_contrato")),
    )
    op.create_index(op.f("ix_pncp_contrato_fornecedor_cnpj"), "pncp_contrato", ["fornecedor_cnpj"])
    op.create_index("ix_pncp_contrato_orgao_cnpj", "pncp_contrato", ["orgao_cnpj"])
    op.create_table(
        "pncp_orgao",
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("nome", sa.String(length=300), nullable=False),
        sa.Column("esfera", sa.String(length=1), nullable=True),
        sa.Column("poder", sa.String(length=1), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.PrimaryKeyConstraint("cnpj", name=op.f("pk_pncp_orgao")),
    )
    op.create_table(
        "pncp_dia",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("total_api", sa.Integer(), nullable=False),
        sa.Column("lidos", sa.Integer(), nullable=False),
        sa.Column("receitas", sa.Integer(), nullable=False),
        sa.Column("empenhos", sa.Integer(), nullable=False),
        sa.Column("pessoas_fisicas", sa.Integer(), nullable=False),
        sa.Column("linhas_alvo", sa.Integer(), nullable=False),
        sa.Column("lido_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dia", name=op.f("pk_pncp_dia")),
    )


def downgrade() -> None:
    op.drop_table("pncp_dia")
    op.drop_table("pncp_orgao")
    op.drop_table("pncp_contrato")
    op.drop_table("pncp_soma")
