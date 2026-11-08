"""Obras federais do Obrasgov.br (redesenho, etapa 5)

Só acrescenta duas tabelas novas (nada é alterado nem removido): `obra_federal` (cada obra ou
projeto de investimento com situação, datas, valor previsto e percentual de execução física) e
`obra_federal_municipio` (o município de cada obra, pela geometria). Carga própria
(obrasgov_obras), sem RECARREGAR_DADOS.

Revision ID: 0065_obras_federais
Revises: 0064_resultados_eleicao
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0065_obras_federais"
down_revision: str | None = "0064_resultados_eleicao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "obra_federal",
        sa.Column("id_unico", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=400), nullable=False),
        sa.Column("situacao", sa.String(length=40), nullable=True),
        sa.Column("natureza", sa.String(length=60), nullable=True),
        sa.Column("especie", sa.String(length=60), nullable=True),
        sa.Column("tipo", sa.String(length=120), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("data_inicial_prevista", sa.Date(), nullable=True),
        sa.Column("data_final_prevista", sa.Date(), nullable=True),
        sa.Column("data_inicial_efetiva", sa.Date(), nullable=True),
        sa.Column("data_final_efetiva", sa.Date(), nullable=True),
        sa.Column("data_cadastro", sa.Date(), nullable=True),
        sa.Column("valor_previsto", sa.Numeric(16, 2), nullable=True),
        sa.Column("valor_previsto_federal", sa.Numeric(16, 2), nullable=True),
        sa.Column("responsavel", sa.String(length=300), nullable=True),
        sa.Column("executor", sa.String(length=300), nullable=True),
        sa.Column("percentual_execucao", sa.Numeric(6, 2), nullable=True),
        sa.Column("execucao_atualizada_em", sa.Date(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_obra_federal_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id_unico", name=op.f("pk_obra_federal")),
    )
    op.create_index("ix_obra_federal_uf_situacao", "obra_federal", ["uf", "situacao"])
    op.create_table(
        "obra_federal_municipio",
        sa.Column("obra_id", sa.String(length=20), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.ForeignKeyConstraint(
            ["obra_id"],
            ["obra_federal.id_unico"],
            name=op.f("fk_obra_federal_municipio_obra_id_obra_federal"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "obra_id", "municipio_ibge", name=op.f("pk_obra_federal_municipio")
        ),
    )
    op.create_index("ix_obra_federal_municipio_ibge", "obra_federal_municipio", ["municipio_ibge"])


def downgrade() -> None:
    op.drop_index("ix_obra_federal_municipio_ibge", table_name="obra_federal_municipio")
    op.drop_table("obra_federal_municipio")
    op.drop_index("ix_obra_federal_uf_situacao", table_name="obra_federal")
    op.drop_table("obra_federal")
