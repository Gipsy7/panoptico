"""Dinheiro federal por estado e cidade

Só aditiva: tabelas novas `arrecadacao_uf` (Receita Federal), `populacao_ibge` (IBGE) e
`transferencia_uniao` (repasses da União; carregada por outra ingestão) e duas colunas
opcionais em `contas_municipio` (`receita_propria`, `transf_uniao`, do SICONFI).

Não precisa de RECARREGAR_DADOS: as tabelas novas têm carga própria (ingestão mensal) e
`contas_municipio` ganha as colunas na próxima carga mensal do SICONFI.

Revision ID: 0051_dinheiro_federal
Revises: 0050_emenda_pagamento_sem_codigo
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0051_dinheiro_federal"
down_revision: str | None = "0050_emenda_pagamento_sem_codigo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arrecadacao_uf",
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("previdencia", sa.Numeric(18, 2), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_arrecadacao_uf_ingestao_id_fonte_ingestao"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uf", "ano", "mes", name=op.f("pk_arrecadacao_uf")),
    )
    op.create_table(
        "populacao_ibge",
        sa.Column("codigo", sa.String(length=7), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("valor", sa.BigInteger(), nullable=False),
        sa.Column("origem", sa.String(length=12), nullable=False),
        sa.PrimaryKeyConstraint("codigo", "ano", name=op.f("pk_populacao_ibge")),
    )
    op.create_table(
        "transferencia_uniao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("bloco", sa.String(length=24), nullable=False),
        sa.Column("fonte", sa.String(length=16), nullable=False),
        sa.Column("valor", sa.Numeric(18, 2), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_transferencia_uniao_ingestao_id_fonte_ingestao"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transferencia_uniao")),
    )
    op.create_index("ix_transferencia_uniao_ano_uf", "transferencia_uniao", ["ano", "uf"])
    op.create_index(
        "ix_transferencia_uniao_municipio_ano", "transferencia_uniao", ["municipio_ibge", "ano"]
    )
    op.add_column(
        "contas_municipio", sa.Column("receita_propria", sa.Numeric(16, 2), nullable=True)
    )
    op.add_column("contas_municipio", sa.Column("transf_uniao", sa.Numeric(16, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("contas_municipio", "transf_uniao")
    op.drop_column("contas_municipio", "receita_propria")
    op.drop_index("ix_transferencia_uniao_municipio_ano", table_name="transferencia_uniao")
    op.drop_index("ix_transferencia_uniao_ano_uf", table_name="transferencia_uniao")
    op.drop_table("transferencia_uniao")
    op.drop_table("populacao_ibge")
    op.drop_table("arrecadacao_uf")
