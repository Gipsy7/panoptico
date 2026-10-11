"""Emendas de relator-geral (RP9): indicações da planilha oficial da CMO com o parlamentar

Só aditiva: tabela nova `emenda_relator_indicacao`.

Revision ID: 0042_emenda_relator
Revises: 0041_cargo_especial_cpgf
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0042_emenda_relator"
down_revision: str | None = "0041_cargo_especial_cpgf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emenda_relator_indicacao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("data_cadastro", sa.Date(), nullable=True),
        sa.Column("parlamentar_id", sa.Integer(), nullable=False),
        sa.Column("autor_nome", sa.String(length=200), nullable=False),
        sa.Column("beneficiario", sa.String(length=300), nullable=False),
        sa.Column("beneficiario_cnpj", sa.String(length=20), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("orgao", sa.String(length=150), nullable=True),
        sa.Column("unidade", sa.String(length=200), nullable=True),
        sa.Column("acao", sa.String(length=20), nullable=True),
        sa.Column("objeto", sa.String(length=500), nullable=True),
        sa.Column("valor_solicitado", sa.Numeric(16, 2), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_relator_indicacao_ingestao_id_fonte_ingestao"),
        ),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_emenda_relator_indicacao_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_relator_indicacao")),
        sa.UniqueConstraint("numero", name=op.f("uq_emenda_relator_indicacao_numero")),
    )
    op.create_index(
        "ix_emenda_relator_parlamentar", "emenda_relator_indicacao", ["parlamentar_id", "ano"]
    )


def downgrade() -> None:
    op.drop_index("ix_emenda_relator_parlamentar", table_name="emenda_relator_indicacao")
    op.drop_table("emenda_relator_indicacao")
