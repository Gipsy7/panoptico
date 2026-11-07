"""Avisar erro, direito de resposta e correções públicas (Frente 7)

Só acrescenta três tabelas novas (nada é alterado nem removido): `sugestao` (avisos de erro e
respostas de quem é citado, com a revisão humana), `sugestao_contato` (contato opcional, à parte
para ficar fora do backup e ser apagado em 180 dias) e `correcao` (correções públicas). Sem IP.
Sem RECARREGAR_DADOS.

Revision ID: 0061_sugestoes_correcoes
Revises: 0060_repasse_estado_municipio
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0061_sugestoes_correcoes"
down_revision: str | None = "0060_repasse_estado_municipio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sugestao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("categoria", sa.String(length=20), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("pagina", sa.String(length=300), nullable=False),
        sa.Column("secao", sa.String(length=120), nullable=True),
        sa.Column("perfil_tipo", sa.String(length=30), nullable=True),
        sa.Column("perfil_id", sa.String(length=40), nullable=True),
        sa.Column("confirmacao", sa.String(length=20), nullable=True),
        sa.Column("protocolo", sa.String(length=12), nullable=False, unique=True),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="nova"),
        sa.Column(
            "criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revisada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publicada_em", sa.Date(), nullable=True),
        sa.Column("nota_revisao", sa.Text(), nullable=True),
    )
    op.create_index("ix_sugestao_perfil", "sugestao", ["perfil_tipo", "perfil_id", "status"])
    op.create_table(
        "sugestao_contato",
        sa.Column(
            "sugestao_id",
            sa.Integer(),
            sa.ForeignKey("sugestao.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("contato", sa.String(length=200), nullable=False),
        sa.Column(
            "criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sugestao_contato_criada_em", "sugestao_contato", ["criada_em"])
    op.create_table(
        "correcao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("dado", sa.String(length=200), nullable=False),
        sa.Column("antes", sa.Text(), nullable=False),
        sa.Column("depois", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("fonte", sa.String(length=500), nullable=False),
        sa.Column("perfil_tipo", sa.String(length=30), nullable=True),
        sa.Column("perfil_id", sa.String(length=40), nullable=True),
        sa.Column(
            "sugestao_id",
            sa.Integer(),
            sa.ForeignKey("sugestao.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_correcao_data", "correcao", ["data"])
    op.create_index("ix_correcao_perfil", "correcao", ["perfil_tipo", "perfil_id"])


def downgrade() -> None:
    op.drop_table("correcao")
    op.drop_table("sugestao_contato")
    op.drop_table("sugestao")
