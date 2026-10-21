"""Discursos em Plenário dos dias de votação nominal

Só aditiva: tabela `discurso` (sumário oficial e links; nunca a transcrição), ligada ao
parlamentar e, quando o sumário cita 1 ou 2 matérias votadas no dia, ao projeto. Sem
RECARREGAR_DADOS: a carga própria (camara_discursos, senado_discursos) preenche.

Revision ID: 0053_discurso
Revises: 0052_gasto_local_fora
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0053_discurso"
down_revision: str | None = "0052_gasto_local_fora"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("discurso"):
        return
    op.create_table(
        "discurso",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("casa", sa.String(length=10), nullable=False),
        sa.Column("id_externo", sa.String(length=60), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("data_hora", sa.DateTime(), nullable=True),
        sa.Column("sessao_id_externo", sa.String(length=30), nullable=True),
        sa.Column("fase", sa.String(length=120), nullable=True),
        sa.Column("tipo", sa.String(length=120), nullable=True),
        sa.Column("sumario", sa.Text(), nullable=True),
        sa.Column("url_texto", sa.Text(), nullable=True),
        sa.Column("url_video", sa.Text(), nullable=True),
        sa.Column("proposicao_id_externo", sa.String(length=30), nullable=True),
        sa.Column("materias_citadas", sa.Integer(), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_discurso_parlamentar_id_parlamentar"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_discurso_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discurso")),
        sa.UniqueConstraint("casa", "id_externo", name="uq_discurso_casa_id_externo"),
    )
    op.create_index(op.f("ix_discurso_parlamentar_id"), "discurso", ["parlamentar_id"])
    op.create_index(
        "ix_discurso_casa_proposicao_data",
        "discurso",
        ["casa", "proposicao_id_externo", "data"],
    )
    op.create_index("ix_discurso_casa_data", "discurso", ["casa", "data"])


def downgrade() -> None:
    op.drop_table("discurso")
