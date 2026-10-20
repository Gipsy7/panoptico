"""Pagamentos de emenda sem código no arquivo por favorecido da CGU

Só aditiva: `emenda_pagamento_sem_codigo`, carregada por ingestion/transparencia/emendas.py
junto com `emenda_pagamento`. São as linhas com código da emenda "Sem informação" (emendas de
2014 a 2020 sem identificação na base da CGU): a fonte traz o tipo e o mês do pagamento, não
o autor nem o ano da emenda. ~29 mil linhas no Brasil. Sem RECARREGAR_DADOS: a próxima carga
normal de `transparencia_emendas` preenche (o contexto da carga incremental mudou).

Revision ID: 0050_emenda_pagamento_sem_codigo
Revises: 0049_emenda_estadual
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0050_emenda_pagamento_sem_codigo"
down_revision: str | None = "0049_emenda_estadual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("emenda_pagamento_sem_codigo"):
        return
    op.create_table(
        "emenda_pagamento_sem_codigo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ano_mes", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=12), nullable=True),
        sa.Column("autor_codigo", sa.String(length=20), nullable=False),
        sa.Column("autor_nome", sa.String(length=200), nullable=False),
        sa.Column("favorecido", sa.String(length=300), nullable=False),
        sa.Column("favorecido_codigo", sa.String(length=20), nullable=False),
        sa.Column("natureza", sa.String(length=100), nullable=False),
        sa.Column("grupo", sa.String(length=20), nullable=False),
        sa.Column("municipio_ibge", sa.String(length=7), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("ingestao_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ingestao_id"],
            ["fonte_ingestao.id"],
            name=op.f("fk_emenda_pagamento_sem_codigo_ingestao_id_fonte_ingestao"),
        ),
        sa.ForeignKeyConstraint(
            ["municipio_ibge"],
            ["municipio.ibge"],
            name=op.f("fk_emenda_pagamento_sem_codigo_municipio_ibge_municipio"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emenda_pagamento_sem_codigo")),
    )
    op.create_index(
        "ix_emenda_pagamento_sem_codigo_municipio",
        "emenda_pagamento_sem_codigo",
        ["municipio_ibge"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("emenda_pagamento_sem_codigo")
