"""mandato_local e projeto_local: vereadores no cargo e projetos (SAPL)

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mandato_local",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("nome_completo", sa.String(length=200), nullable=True),
        sa.Column("partido", sa.String(length=30), nullable=True),
        sa.Column("foto_url", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("telefone", sa.String(length=60), nullable=True),
        sa.Column("titular", sa.Boolean(), nullable=False),
        sa.Column("em_exercicio", sa.Boolean(), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=True),
        sa.Column("fim", sa.Date(), nullable=True),
        sa.Column("proposicoes_por_tipo", sa.JSON(), nullable=False),
        sa.Column("candidatura_id", sa.Integer(), nullable=True),
        sa.Column("sapl_url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_mandato_local_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidatura_id"],
            ["candidatura.id"],
            name=op.f("fk_mandato_local_candidatura_id_candidatura"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mandato_local")),
        sa.UniqueConstraint(
            "municipio_ibge", "id_externo", name=op.f("uq_mandato_local_municipio_ibge")
        ),
    )
    op.create_index(op.f("ix_mandato_local_municipio_ibge"), "mandato_local", ["municipio_ibge"])
    op.create_table(
        "projeto_local",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("mandato_id", sa.Integer(), nullable=False),
        sa.Column("id_externo", sa.String(length=20), nullable=False),
        sa.Column("tipo", sa.String(length=120), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.Column("data_apresentacao", sa.Date(), nullable=True),
        sa.Column("em_tramitacao", sa.Boolean(), nullable=True),
        sa.Column("primeiro_autor", sa.Boolean(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_projeto_local_municipio_ibge_municipio"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mandato_id"],
            ["mandato_local.id"],
            name=op.f("fk_projeto_local_mandato_id_mandato_local"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projeto_local")),
        sa.UniqueConstraint("mandato_id", "id_externo", name=op.f("uq_projeto_local_mandato_id")),
    )
    op.create_index(op.f("ix_projeto_local_municipio_ibge"), "projeto_local", ["municipio_ibge"])
    op.create_index("ix_projeto_local_mandato", "projeto_local", ["mandato_id"])


def downgrade() -> None:
    op.drop_index("ix_projeto_local_mandato", table_name="projeto_local")
    op.drop_index(op.f("ix_projeto_local_municipio_ibge"), table_name="projeto_local")
    op.drop_table("projeto_local")
    op.drop_index(op.f("ix_mandato_local_municipio_ibge"), table_name="mandato_local")
    op.drop_table("mandato_local")
