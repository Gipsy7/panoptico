"""Cadastro de empresas por CNPJ (razão social, natureza jurídica, município)

Só aditiva: tabela nova `empresa`, carregada por ingestion/receita/empresas.py a partir da base
aberta do CNPJ da Receita (só os CNPJs de interesse). Defensiva: se a tabela já existe (criada
no acervo antes da migração), não faz nada.

Revision ID: 0046_empresa
Revises: 0045_orientacao_partidos
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0046_empresa"
down_revision: str | None = "0045_orientacao_partidos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("empresa"):
        return
    op.create_table(
        "empresa",
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("razao_social", sa.String(length=300), nullable=True),
        sa.Column("nome_omitido", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("nome_fantasia", sa.String(length=300), nullable=True),
        sa.Column("natureza_juridica", sa.String(length=4), nullable=True),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("situacao", sa.String(length=2), nullable=True),
        sa.Column("referencia", sa.String(length=10), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cnpj", name=op.f("pk_empresa")),
    )
    op.create_index("ix_empresa_municipio", "empresa", ["municipio_ibge"])


def downgrade() -> None:
    op.drop_index("ix_empresa_municipio", table_name="empresa", if_exists=True)
    op.drop_table("empresa", if_exists=True)
