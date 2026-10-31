"""Avisos por Web Push: fatos detectados, inscrições, alvos e cursor por ambiente

Só acrescenta quatro tabelas novas (nada é alterado nem removido). `aviso_evento` não tem dado de
cidadão; `aviso_inscricao` e `aviso_alvo` ficam fora dos backups. Sem RECARREGAR_DADOS.

Revision ID: 0058_avisos_web_push
Revises: 0057_argos_registros
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_avisos_web_push"
down_revision: str | None = "0057_argos_registros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "aviso_evento",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("alvo_tipo", sa.String(length=12), nullable=False),
        sa.Column("alvo_chave", sa.String(length=45), nullable=False),
        sa.Column("categoria", sa.String(length=12), nullable=False),
        sa.Column("chave_natural", sa.String(length=200), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("caminho", sa.String(length=120), nullable=False),
        sa.Column("fonte", sa.String(length=120), nullable=False),
        sa.Column("data_fato", sa.Date(), nullable=False),
        sa.Column("detectado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "alvo_tipo", "alvo_chave", "categoria", "chave_natural", name="uq_aviso_evento_chave"
        ),
    )
    op.create_index("ix_aviso_evento_detectado_em", "aviso_evento", ["detectado_em"])
    op.create_table(
        "aviso_inscricao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ambiente", sa.String(length=20), nullable=False),
        sa.Column("endpoint", sa.String(length=1000), nullable=False),
        sa.Column("p256dh", sa.String(length=256), nullable=False),
        sa.Column("auth", sa.String(length=64), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultimo_sucesso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_evento_id", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("ambiente", "endpoint", name="uq_aviso_inscricao_ambiente_endpoint"),
    )
    op.create_table(
        "aviso_alvo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "inscricao_id",
            sa.Integer(),
            sa.ForeignKey(
                "aviso_inscricao.id",
                name=op.f("fk_aviso_alvo_inscricao_id_aviso_inscricao"),
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("alvo_tipo", sa.String(length=12), nullable=False),
        sa.Column("alvo_chave", sa.String(length=45), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("inscricao_id", "alvo_tipo", "alvo_chave", name="uq_aviso_alvo_chave"),
    )
    op.create_table(
        "aviso_cursor",
        sa.Column("ambiente", sa.String(length=20), primary_key=True),
        sa.Column("ultimo_evento_id", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("aviso_cursor")
    op.drop_table("aviso_alvo")
    op.drop_table("aviso_inscricao")
    op.drop_table("aviso_evento")
