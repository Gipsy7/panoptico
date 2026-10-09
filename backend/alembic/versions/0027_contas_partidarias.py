"""contas partidárias: somas anuais, cotas mensais, despesas vinculadas e FEFC/FP

Revision ID: 0027_contas_partidarias
Revises: 0026
Create Date: 2026-10-09

Aditiva: só cria tabelas. O id da revisão é um texto único (e não "0027") porque outra
frente pode criar a 0027 em paralelo; a ordem é acertada no merge.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_contas_partidarias"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partido_conta_soma",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=False),
        sa.Column("esfera", sa.String(length=20), nullable=False),
        sa.Column("uf", sa.String(length=2), server_default="", nullable=False),
        sa.Column("fonte_recurso", sa.String(length=60), nullable=False),
        sa.Column("natureza", sa.String(length=30), nullable=False),
        sa.Column("categoria", sa.String(length=200), nullable=False),
        sa.Column("valor", sa.Numeric(16, 2), nullable=False),
        sa.Column("lancamentos", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partido_conta_soma")),
        sa.UniqueConstraint(
            "ano",
            "tipo",
            "partido",
            "esfera",
            "uf",
            "fonte_recurso",
            "natureza",
            "categoria",
            name=op.f("uq_partido_conta_soma_ano"),
        ),
    )
    op.create_index("ix_partido_conta_soma_ano_partido", "partido_conta_soma", ["ano", "partido"])
    op.create_table(
        "partido_cota_mensal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Date(), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=False),
        sa.Column("fundo", sa.String(length=30), nullable=False),
        sa.Column("valor", sa.Numeric(16, 2), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partido_cota_mensal")),
        sa.UniqueConstraint(
            "ano", "mes", "partido", "fundo", name=op.f("uq_partido_cota_mensal_ano")
        ),
    )
    op.create_table(
        "partido_despesa_vinculada",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=False),
        sa.Column("esfera", sa.String(length=20), nullable=False),
        sa.Column("uf", sa.String(length=2), server_default="", nullable=False),
        sa.Column("municipio", sa.String(length=120), nullable=True),
        sa.Column("sq_despesa", sa.String(length=20), nullable=True),
        sa.Column("fornecedor_cnpj", sa.String(length=14), nullable=True),
        sa.Column("fornecedor_nome", sa.String(length=300), nullable=True),
        sa.Column("pessoa_id", sa.Integer(), nullable=True),
        sa.Column("motivo", sa.String(length=60), nullable=False),
        sa.Column("categoria", sa.String(length=200), nullable=False),
        sa.Column("fonte_recurso", sa.String(length=60), nullable=False),
        sa.Column("natureza", sa.String(length=30), nullable=False),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("valor", sa.Numeric(16, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_partido_despesa_vinculada_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partido_despesa_vinculada")),
    )
    op.create_index(
        "ix_partido_despesa_vinculada_ano_partido",
        "partido_despesa_vinculada",
        ["ano", "partido"],
    )
    op.create_index(
        op.f("ix_partido_despesa_vinculada_fornecedor_cnpj"),
        "partido_despesa_vinculada",
        ["fornecedor_cnpj"],
    )
    op.create_index(
        op.f("ix_partido_despesa_vinculada_pessoa_id"), "partido_despesa_vinculada", ["pessoa_id"]
    )
    op.create_table(
        "partido_fefc_fp",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("fundo", sa.String(length=10), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=False),
        sa.Column("esfera", sa.String(length=20), nullable=False),
        sa.Column("genero", sa.String(length=20), nullable=False),
        sa.Column("cor_raca", sa.String(length=20), server_default="", nullable=False),
        sa.Column("candidatos", sa.Integer(), nullable=False),
        sa.Column("valor_recebido", sa.Numeric(16, 2), nullable=False),
        sa.Column("valor_minimo_cota", sa.Numeric(16, 2), nullable=True),
        sa.Column("valor_partido", sa.Numeric(16, 2), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partido_fefc_fp")),
        sa.UniqueConstraint(
            "ano",
            "fundo",
            "partido",
            "esfera",
            "genero",
            "cor_raca",
            name=op.f("uq_partido_fefc_fp_ano"),
        ),
    )


def downgrade() -> None:
    op.drop_table("partido_fefc_fp")
    op.drop_table("partido_despesa_vinculada")
    op.drop_table("partido_cota_mensal")
    op.drop_table("partido_conta_soma")
