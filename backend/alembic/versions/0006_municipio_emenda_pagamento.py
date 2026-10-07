"""municipio e emenda_pagamento

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "municipio",
        sa.Column("ibge", sa.String(length=7), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("nome_chave", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("ibge", name=op.f("pk_municipio")),
    )
    op.create_index(op.f("ix_municipio_uf"), "municipio", ["uf"])
    op.create_table(
        "emenda_pagamento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emenda_codigo", sa.String(length=20), nullable=False),
        sa.Column("ano_emenda", sa.SmallInteger(), nullable=False),
        sa.Column("ano_mes", sa.Integer(), nullable=False),
        sa.Column("autor_codigo", sa.String(length=20), nullable=False),
        sa.Column("autor_nome", sa.String(length=200), nullable=False),
        sa.Column("parlamentar_id", sa.Integer(), nullable=True),
        sa.Column("favorecido", sa.String(length=300), nullable=False),
        sa.Column("favorecido_codigo", sa.String(length=20), nullable=False),
        sa.Column("natureza", sa.String(length=100), nullable=False),
        sa.Column("grupo", sa.String(length=20), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("valor", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_pagamento_ingestao_id_fonte_ingestao"),
        ),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_emenda_pagamento_municipio_ibge_municipio"),
        ),
        sa.ForeignKeyConstraint(
            ["parlamentar_id"],
            ["parlamentar.id"],
            name=op.f("fk_emenda_pagamento_parlamentar_id_parlamentar"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_pagamento")),
    )
    op.create_index(
        "ix_emenda_pagamento_municipio", "emenda_pagamento", ["municipio_ibge", "ano_emenda"]
    )
    op.create_index("ix_emenda_pagamento_parlamentar", "emenda_pagamento", ["parlamentar_id"])


def downgrade() -> None:
    op.drop_index("ix_emenda_pagamento_parlamentar", table_name="emenda_pagamento")
    op.drop_index("ix_emenda_pagamento_municipio", table_name="emenda_pagamento")
    op.drop_table("emenda_pagamento")
    op.drop_index(op.f("ix_municipio_uf"), table_name="municipio")
    op.drop_table("municipio")
