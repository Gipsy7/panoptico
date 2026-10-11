"""servidor_federal.origem (cargos de natureza especial vindos das viagens) e cpgf_portador_mes

Aditiva: coluna com padrão 'siape', `id_portal` passa a aceitar nulo (cargos vindos das
viagens não têm id de servidor) e tabela nova do cartão de pagamento do governo federal.

Revision ID: 0041_cargo_especial_cpgf
Revises: 0040_transferegov
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_cargo_especial_cpgf"
down_revision: str | None = "0040_transferegov"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "servidor_federal",
        sa.Column("origem", sa.String(length=20), nullable=False, server_default="siape"),
    )
    op.alter_column("servidor_federal", "id_portal", existing_type=sa.Integer(), nullable=True)
    op.create_table(
        "cpgf_portador_mes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("orgao", sa.String(length=160), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("transacoes", sa.Integer(), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("saques", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["pessoa_id"], ["pessoa.id"],
            name=op.f("fk_cpgf_portador_mes_pessoa_id_pessoa"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpgf_portador_mes")),
        sa.UniqueConstraint("pessoa_id", "orgao", "ano", "mes",
                            name=op.f("uq_cpgf_portador_mes_pessoa_id")),
    )  # fmt: skip


def downgrade() -> None:
    op.drop_table("cpgf_portador_mes")
    op.execute("DELETE FROM servidor_federal WHERE id_portal IS NULL")
    op.alter_column("servidor_federal", "id_portal", existing_type=sa.Integer(), nullable=False)
    op.drop_column("servidor_federal", "origem")
