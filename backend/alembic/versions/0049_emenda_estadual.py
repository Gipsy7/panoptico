"""Emendas parlamentares estaduais (começando por Santa Catarina)

Só aditiva: `emenda_estadual`, carregada por ingestion/emendas_estaduais/sc.py a partir do SC
Transferências (CGE/SC): uma linha por proposta de transferência aberta a partir de uma
emenda impositiva da ALESC, com autor, município, favorecido (CNPJ) e valores previsto,
empenhado e pago separados. Sem RECARREGAR_DADOS: carga própria.

Revision ID: 0049_emenda_estadual
Revises: 0048_eagendas
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049_emenda_estadual"
down_revision: str | None = "0048_eagendas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("emenda_estadual"):
        return
    op.create_table(
        "emenda_estadual",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("ano", sa.SmallInteger(), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("proposta", sa.String(length=20), nullable=False),
        sa.Column("transferencia", sa.String(length=20), nullable=True),
        sa.Column("tipo", sa.String(length=12), nullable=False),
        sa.Column("autor_nome", sa.String(length=200), nullable=False),
        sa.Column("autor_chave", sa.String(length=200), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=True),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=True),
        sa.Column("municipio_nome", sa.String(length=100), nullable=False),
        sa.Column("favorecido_nome", sa.String(length=300), nullable=True),
        sa.Column("favorecido_cnpj", sa.String(length=14), nullable=True),
        sa.Column("favorecido_natureza", sa.String(length=80), nullable=True),
        sa.Column("orgao", sa.String(length=200), nullable=True),
        sa.Column("instrumento", sa.String(length=40), nullable=True),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("situacao_proposta", sa.String(length=60), nullable=True),
        sa.Column("situacao_transferencia", sa.String(length=40), nullable=True),
        sa.Column("valor_previsto", sa.Numeric(14, 2), nullable=False),
        sa.Column("valor_empenhado", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_pago", sa.Numeric(14, 2), nullable=False),
        sa.Column("fonte", sa.String(length=40), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_estadual_ingestao_id_fonte_ingestao"),
        ),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_emenda_estadual_municipio_ibge_municipio"),
        ),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_emenda_estadual_pessoa_id_pessoa"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_estadual")),
        sa.UniqueConstraint("uf", "proposta", name=op.f("uq_emenda_estadual_uf")),
    )
    op.create_index(
        "ix_emenda_estadual_municipio", "emenda_estadual", ["municipio_ibge", "ano"], unique=False
    )
    op.create_index(
        "ix_emenda_estadual_uf_autor", "emenda_estadual", ["uf", "autor_chave"], unique=False
    )
    op.create_index(
        op.f("ix_emenda_estadual_pessoa_id"), "emenda_estadual", ["pessoa_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("emenda_estadual")
