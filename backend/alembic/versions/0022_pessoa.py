"""pessoa, pessoa_vinculo e evento: identidade única de pessoa pública e linha do tempo;
candidatura.data_eleicao (data do turno que definiu o resultado)

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidatura", sa.Column("data_eleicao", sa.Date(), nullable=True))
    op.create_table(
        "pessoa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("chave_nome", sa.String(length=200), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("titulo", sa.String(length=12), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pessoa")),
    )
    op.create_index(op.f("ix_pessoa_chave_nome"), "pessoa", ["chave_nome"])
    op.create_index(op.f("ix_pessoa_cpf"), "pessoa", ["cpf"])
    op.create_index(op.f("ix_pessoa_titulo"), "pessoa", ["titulo"])

    op.create_table(
        "pessoa_vinculo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("fonte", sa.String(length=40), nullable=False),
        sa.Column("id_externo", sa.String(length=80), nullable=False),
        sa.Column("regra", sa.String(length=30), nullable=False),
        sa.Column("revisado", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_pessoa_vinculo_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pessoa_vinculo")),
        sa.UniqueConstraint("fonte", "id_externo", name=op.f("uq_pessoa_vinculo_fonte")),
    )
    op.create_index(op.f("ix_pessoa_vinculo_pessoa_id"), "pessoa_vinculo", ["pessoa_id"])

    op.create_table(
        "evento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("vinculo_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("orgao", sa.String(length=120), nullable=True),
        sa.Column("numero_processo", sa.String(length=40), nullable=True),
        sa.Column("situacao", sa.String(length=80), nullable=True),
        sa.Column("fonte", sa.String(length=50), nullable=False),
        sa.Column("id_externo", sa.String(length=100), nullable=False),
        sa.Column("fonte_url", sa.Text(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_evento_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vinculo_id"],
            ["pessoa_vinculo.id"],
            name=op.f("fk_evento_vinculo_id_pessoa_vinculo"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_evento_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evento")),
        sa.UniqueConstraint("fonte", "id_externo", "tipo", name=op.f("uq_evento_fonte")),
    )
    op.create_index("ix_evento_pessoa_data", "evento", ["pessoa_id", "data"])
    op.create_index(op.f("ix_evento_vinculo_id"), "evento", ["vinculo_id"])


def downgrade() -> None:
    op.drop_table("evento")
    op.drop_table("pessoa_vinculo")
    op.drop_table("pessoa")
    op.drop_column("candidatura", "data_eleicao")
