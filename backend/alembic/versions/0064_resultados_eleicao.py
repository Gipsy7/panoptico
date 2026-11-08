"""Eleições completas (Frente 5): resultado por candidato e totais de comparecimento

Só acrescenta duas tabelas novas (nada é alterado nem removido): `resultado_candidato` (votos de
cada candidato na disputa e, nas eleições gerais, o recorte por município) e `resultado_totais`
(aptos, comparecimento, brancos e nulos por cargo, município e turno). Carga própria
(tse_resultados), sem RECARREGAR_DADOS.

Revision ID: 0064_resultados_eleicao
Revises: 0063_tipo_votacao
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0064_resultados_eleicao"
down_revision: str | None = "0063_tipo_votacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resultado_candidato",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("turno", sa.SmallInteger(), nullable=False),
        sa.Column("cargo", sa.String(length=40), nullable=False),
        sa.Column("abrangencia", sa.String(length=10), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("sq_candidato", sa.String(length=30), nullable=False),
        sa.Column("numero", sa.String(length=10), nullable=True),
        sa.Column("nome_urna", sa.String(length=120), nullable=False),
        sa.Column("partido", sa.String(length=30), nullable=True),
        sa.Column("votos", sa.Integer(), nullable=False),
        sa.Column("situacao", sa.String(length=40), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_resultado_candidato_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resultado_candidato")),
    )
    op.create_index(
        "ix_resultado_candidato_disputa",
        "resultado_candidato",
        ["ano", "cargo", "turno", "abrangencia", "uf", "municipio_ibge"],
    )
    op.create_index("ix_resultado_candidato_sq", "resultado_candidato", ["ano", "sq_candidato"])
    op.create_table(
        "resultado_totais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("turno", sa.SmallInteger(), nullable=False),
        sa.Column("cargo", sa.String(length=40), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("aptos", sa.Integer(), nullable=False),
        sa.Column("comparecimento", sa.Integer(), nullable=False),
        sa.Column("abstencoes", sa.Integer(), nullable=False),
        sa.Column("brancos", sa.Integer(), nullable=False),
        sa.Column("nulos", sa.Integer(), nullable=False),
        sa.Column("validos", sa.Integer(), nullable=False),
        sa.Column("nominais", sa.Integer(), nullable=False),
        sa.Column("votos_em_eleitos", sa.Integer(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_resultado_totais_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resultado_totais")),
    )
    op.create_index(
        "ix_resultado_totais_mun",
        "resultado_totais",
        ["ano", "cargo", "turno", "municipio_ibge"],
        unique=True,
    )
    op.create_index("ix_resultado_totais_uf", "resultado_totais", ["ano", "cargo", "turno", "uf"])


def downgrade() -> None:
    op.drop_index("ix_resultado_totais_uf", table_name="resultado_totais")
    op.drop_index("ix_resultado_totais_mun", table_name="resultado_totais")
    op.drop_table("resultado_totais")
    op.drop_index("ix_resultado_candidato_sq", table_name="resultado_candidato")
    op.drop_index("ix_resultado_candidato_disputa", table_name="resultado_candidato")
    op.drop_table("resultado_candidato")
