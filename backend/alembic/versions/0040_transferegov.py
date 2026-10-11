"""TransfereGov: o que aconteceu com o dinheiro das emendas (convênios e transferências especiais)

Só aditiva: tabelas novas `emenda_convenio` (ligação emenda -> convênio) e
`emenda_transferencia` (situação, valores, vigência e prestação de contas).

Revision ID: 0040_transferegov
Revises: 0039_servidor_federal
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0040_transferegov"
down_revision: str | None = "0039_servidor_federal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emenda_convenio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("emenda_codigo", sa.String(length=20), nullable=False),
        sa.Column("numero_convenio", sa.String(length=20), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_convenio_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_convenio")),
        sa.UniqueConstraint(
            "emenda_codigo", "numero_convenio", name=op.f("uq_emenda_convenio_emenda_codigo")
        ),
    )
    op.create_index("ix_emenda_convenio_numero", "emenda_convenio", ["numero_convenio"])
    op.create_table(
        "emenda_transferencia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("emenda_codigo", sa.String(length=20), nullable=False),
        sa.Column("ano_emenda", sa.SmallInteger(), nullable=False),
        sa.Column("identificador", sa.String(length=30), nullable=False),
        sa.Column("situacao", sa.String(length=120), nullable=True),
        sa.Column("relatorio_gestao", sa.String(length=60), nullable=True),
        sa.Column("beneficiario", sa.String(length=300), nullable=True),
        sa.Column("beneficiario_cnpj", sa.String(length=20), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("orgao_concedente", sa.String(length=200), nullable=True),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("valor_total", sa.Numeric(16, 2), nullable=True),
        sa.Column("valor_repassado", sa.Numeric(16, 2), nullable=True),
        sa.Column("valor_contrapartida", sa.Numeric(16, 2), nullable=True),
        sa.Column("inicio_vigencia", sa.Date(), nullable=True),
        sa.Column("fim_vigencia", sa.Date(), nullable=True),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_transferencia_ingestao_id_fonte_ingestao"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_transferencia")),
        sa.UniqueConstraint(
            "tipo", "identificador", "emenda_codigo", name=op.f("uq_emenda_transferencia_tipo")
        ),
    )
    op.create_index("ix_emenda_transferencia_emenda", "emenda_transferencia", ["emenda_codigo"])


def downgrade() -> None:
    op.drop_table("emenda_transferencia")
    op.drop_table("emenda_convenio")
