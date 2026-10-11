"""PNCP: contratos com valor suspeito ficam fora das somas e guardados à parte

Só aditiva: tabela `pncp_suspeito` (o que sai de `pncp_janela`/`pncp_anual`) e a coluna
`pncp_contrato.valor_suspeito` (padrão falso, preenchida aqui para o que já existe). Regra em
`ingestion/pncp/suspeito.py`: valor acima do menor entre a despesa paga anual do município
(SICONFI, órgão municipal) e R$ 50 bilhões.

Revision ID: 0035_pncp_suspeito
Revises: 0034_pncp_anual
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_pncp_suspeito"
down_revision: str | None = "0034_pncp_anual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pncp_contrato",
        sa.Column("valor_suspeito", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "pncp_suspeito",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("orgao_cnpj", sa.String(length=14), nullable=False),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=False),
        sa.Column("referencia", sa.String(length=40), server_default="", nullable=False),
        sa.Column("fornecedor_nome", sa.String(length=120), nullable=True),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor_global", sa.Numeric(18, 2), nullable=False),
        sa.Column("limite", sa.Numeric(18, 2), nullable=False),
        sa.PrimaryKeyConstraint(
            "dia", "municipio_ibge", "orgao_cnpj", "fornecedor_cnpj", "referencia",
            name=op.f("pk_pncp_suspeito"),
        ),
    )  # fmt: skip
    op.create_index("ix_pncp_suspeito_municipio", "pncp_suspeito", ["municipio_ibge", "dia"])
    # Mesma regra de ingestion/pncp/suspeito.py, para os contratos que já estão no banco.
    op.execute(
        """
        UPDATE pncp_contrato c SET valor_suspeito = true
        WHERE c.valor_global > LEAST(
            50000000000,
            CASE WHEN c.esfera = 'M' THEN COALESCE((
                SELECT m.despesa_paga FROM contas_municipio m
                WHERE m.municipio_ibge = c.municipio_ibge AND m.despesa_paga > 0
                ORDER BY m.ano DESC LIMIT 1), 50000000000)
            ELSE 50000000000 END)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pncp_suspeito_municipio", table_name="pncp_suspeito")
    op.drop_table("pncp_suspeito")
    op.drop_column("pncp_contrato", "valor_suspeito")
