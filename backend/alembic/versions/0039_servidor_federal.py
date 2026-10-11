"""servidor_federal e viagem_federal_ano: cargos de confiança e viagens das pessoas da base

Aditiva (tabelas novas). down_revision provisória: a head deve ser acertada no merge com a
`0038_transferegov`.

Revision ID: 0039_servidor_federal
Revises: 0037_pncp_salto_de_valor
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0039_servidor_federal"
down_revision: str | None = "0037_pncp_salto_de_valor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "servidor_federal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("id_externo", sa.String(length=100), nullable=False),
        sa.Column("id_portal", sa.Integer(), nullable=False),
        sa.Column("sigla", sa.String(length=10), nullable=False),
        sa.Column("nivel", sa.String(length=6), nullable=True),
        sa.Column("funcao", sa.String(length=120), nullable=False),
        sa.Column("atividade", sa.String(length=120), nullable=True),
        sa.Column("orgao", sa.String(length=120), nullable=True),
        sa.Column("orgao_superior", sa.String(length=120), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("situacao_vinculo", sa.String(length=60), nullable=True),
        sa.Column("data_ingresso", sa.Date(), nullable=True),
        sa.Column("data_nomeacao", sa.Date(), nullable=True),
        sa.Column("primeiro_mes", sa.Date(), nullable=False),
        sa.Column("ultimo_mes", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"], ["pessoa.id"],
            name=op.f("fk_servidor_federal_pessoa_id_pessoa"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_servidor_federal")),
        sa.UniqueConstraint("id_externo", name=op.f("uq_servidor_federal_id_externo")),
    )  # fmt: skip
    op.create_index(op.f("ix_servidor_federal_pessoa_id"), "servidor_federal", ["pessoa_id"])
    op.create_table(
        "viagem_federal_ano",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("viagens", sa.Integer(), nullable=False),
        sa.Column("diarias", sa.Numeric(14, 2), nullable=False),
        sa.Column("passagens", sa.Numeric(14, 2), nullable=False),
        sa.Column("outros", sa.Numeric(14, 2), nullable=False),
        sa.Column("devolucao", sa.Numeric(14, 2), nullable=False),
        sa.Column("ultima_viagem", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pessoa_id"], ["pessoa.id"],
            name=op.f("fk_viagem_federal_ano_pessoa_id_pessoa"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_viagem_federal_ano")),
        sa.UniqueConstraint("pessoa_id", "ano", name=op.f("uq_viagem_federal_ano_pessoa_id")),
    )  # fmt: skip


def downgrade() -> None:
    op.drop_table("viagem_federal_ano")
    op.drop_index(op.f("ix_servidor_federal_pessoa_id"), table_name="servidor_federal")
    op.drop_table("servidor_federal")
