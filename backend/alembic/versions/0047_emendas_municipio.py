"""Emendas por município completas (docs/DECISOES.md, 2026-10-18, "Resgate de cobertura")

Só aditiva, colunas opcionais:
- `emenda_pagamento.tipo`: individual | especial | bancada | comissao | relator (linhas
  antigas ficam nulas até a próxima carga de `transparencia_emendas`, que regrava a tabela);
- `emenda_pagamento.pessoa_id`: autor ligado a `pessoa` por vínculo forte (nome exato);
- `emenda_transferencia.municipio_ibge`: município do beneficiário (CNPJ da prefeitura pelo
  SICONFI, CNPJ de fundo ou entidade pelo arquivo por favorecido, ou nome + UF do convênio).

Sem RECARREGAR_DADOS: a carga diária de emendas e do TransfereGov preenche as colunas novas
na próxima execução (ver DECISOES, "carga na produção").

Revision ID: 0047_emendas_municipio
Revises: 0046_empresa
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0047_emendas_municipio"
down_revision: str | None = "0046_empresa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("emenda_pagamento", sa.Column("tipo", sa.String(length=12), nullable=True))
    op.add_column("emenda_pagamento", sa.Column("pessoa_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_emenda_pagamento_pessoa_id_pessoa"),
        "emenda_pagamento",
        "pessoa",
        ["pessoa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "emenda_transferencia", sa.Column("municipio_ibge", sa.String(length=7), nullable=True)
    )
    op.create_index(
        "ix_emenda_transferencia_municipio",
        "emenda_transferencia",
        ["municipio_ibge"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_emenda_transferencia_municipio", table_name="emenda_transferencia", if_exists=True
    )
    op.drop_column("emenda_transferencia", "municipio_ibge")
    op.drop_constraint(
        op.f("fk_emenda_pagamento_pessoa_id_pessoa"), "emenda_pagamento", type_="foreignkey"
    )
    op.drop_column("emenda_pagamento", "pessoa_id")
    op.drop_column("emenda_pagamento", "tipo")
