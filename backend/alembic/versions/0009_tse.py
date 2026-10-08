"""tse: candidaturas, bens declarados e resumo da campanha

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidatura",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano_eleicao", sa.SmallInteger(), nullable=False),
        sa.Column("sq_candidato", sa.String(length=20), nullable=False),
        sa.Column("cargo", sa.String(length=40), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("unidade", sa.String(length=100), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("nome_urna", sa.String(length=100), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=True),
        sa.Column("numero", sa.String(length=10), nullable=True),
        sa.Column("situacao_turno", sa.String(length=40), nullable=True),
        sa.Column("situacao_candidatura", sa.String(length=40), nullable=True),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("parlamentar_id", sa.Integer(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_candidatura_parlamentar_id_parlamentar"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_candidatura_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidatura")),
        sa.UniqueConstraint("ano_eleicao", "sq_candidato", name=op.f("uq_candidatura_ano_eleicao")),
    )
    op.create_index("ix_candidatura_cpf", "candidatura", ["cpf"])
    op.create_index(op.f("ix_candidatura_parlamentar_id"), "candidatura", ["parlamentar_id"])

    op.create_table(
        "bem_declarado",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidatura_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidatura_id"],
            ["candidatura.id"],
            name=op.f("fk_bem_declarado_candidatura_id_candidatura"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bem_declarado")),
    )
    op.create_index(op.f("ix_bem_declarado_candidatura_id"), "bem_declarado", ["candidatura_id"])

    op.create_table(
        "campanha_resumo",
        sa.Column("candidatura_id", sa.Integer(), nullable=False),
        sa.Column("receitas_total", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("receitas_por_origem", sa.JSON(), nullable=False),
        sa.Column("despesas_total", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("despesas_por_tipo", sa.JSON(), nullable=False),
        sa.Column("numero_doadores", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidatura_id"],
            ["candidatura.id"],
            name=op.f("fk_campanha_resumo_candidatura_id_candidatura"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("candidatura_id", name=op.f("pk_campanha_resumo")),
    )

    op.add_column("parlamentar", sa.Column("cpf", sa.String(length=11), nullable=True))


def downgrade() -> None:
    op.drop_column("parlamentar", "cpf")
    op.drop_table("campanha_resumo")
    op.drop_index(op.f("ix_bem_declarado_candidatura_id"), table_name="bem_declarado")
    op.drop_table("bem_declarado")
    op.drop_index(op.f("ix_candidatura_parlamentar_id"), table_name="candidatura")
    op.drop_index("ix_candidatura_cpf", table_name="candidatura")
    op.drop_table("candidatura")
