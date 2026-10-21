"""Pauta do Plenário e tramitação das proposições

Só aditiva: tabelas `pauta_item` e `tramitacao` (cargas próprias, sem RECARREGAR_DADOS) e as
colunas opcionais `relator` e `relator_parlamentar_id` em `proposicao`.

Revision ID: 0055_pauta_tramitacao
Revises: 0054_discurso
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0055_pauta_tramitacao"
down_revision: str | None = "0054_discurso"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspetor = sa.inspect(op.get_bind())
    if not inspetor.has_table("pauta_item"):
        op.create_table(
            "pauta_item",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("casa", sa.String(length=10), nullable=False),
            sa.Column("data", sa.Date(), nullable=False),
            sa.Column("sessao", sa.String(length=30), nullable=False),
            sa.Column("ordem", sa.SmallInteger(), nullable=True),
            sa.Column("proposicao", sa.String(length=60), nullable=True),
            sa.Column("proposicao_id_externo", sa.String(length=30), nullable=True),
            sa.Column("ementa", sa.Text(), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("ingestao_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["ingestao_id"],
                ["fonte_ingestao.id"],
                name=op.f("fk_pauta_item_ingestao_id_fonte_ingestao"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_pauta_item")),
        )
        op.create_index("ix_pauta_item_casa_data", "pauta_item", ["casa", "data"])
        op.create_index(
            op.f("ix_pauta_item_proposicao_id_externo"), "pauta_item", ["proposicao_id_externo"]
        )
    if not inspetor.has_table("tramitacao"):
        op.create_table(
            "tramitacao",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("casa", sa.String(length=10), nullable=False),
            sa.Column("proposicao_id_externo", sa.String(length=30), nullable=False),
            sa.Column("ordem", sa.SmallInteger(), nullable=False),
            sa.Column("data", sa.DateTime(), nullable=False),
            sa.Column("orgao", sa.String(length=60), nullable=True),
            sa.Column("tipo", sa.String(length=200), nullable=True),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("situacao", sa.String(length=200), nullable=True),
            sa.Column("fonte_marca", sa.String(length=40), nullable=True),
            sa.Column("ingestao_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["ingestao_id"],
                ["fonte_ingestao.id"],
                name=op.f("fk_tramitacao_ingestao_id_fonte_ingestao"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_tramitacao")),
        )
        op.create_index(
            "ix_tramitacao_casa_proposicao_ordem",
            "tramitacao",
            ["casa", "proposicao_id_externo", "ordem"],
        )
    colunas = {c["name"] for c in inspetor.get_columns("proposicao")}
    if "relator" not in colunas:
        op.add_column("proposicao", sa.Column("relator", sa.String(length=200), nullable=True))
    if "relator_parlamentar_id" not in colunas:
        op.add_column(
            "proposicao", sa.Column("relator_parlamentar_id", sa.Integer(), nullable=True)
        )
        op.create_foreign_key(
            op.f("fk_proposicao_relator_parlamentar_id_parlamentar"),
            "proposicao",
            "parlamentar",
            ["relator_parlamentar_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_proposicao_relator_parlamentar_id_parlamentar"), "proposicao", type_="foreignkey"
    )
    op.drop_column("proposicao", "relator_parlamentar_id")
    op.drop_column("proposicao", "relator")
    op.drop_table("tramitacao")
    op.drop_table("pauta_item")
