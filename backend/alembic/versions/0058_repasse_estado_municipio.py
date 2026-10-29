"""Repasses do governo do estado à prefeitura (SICONFI, DCA Anexo I-C)

Acrescenta a coluna opcional `contas_municipio.transf_estado` (JSON com o total e os tipos:
cota-parte do ICMS, do IPVA, do IPI, da CIDE, royalties, SUS, convênios, outras e a parte
retida para o Fundeb). Só acréscimo; nada é removido. Sem RECARREGAR_DADOS: a carga mensal de
`siconfi_contas` preenche a coluna na próxima execução.

Revision ID: 0058_repasse_estado_municipio
Revises: 0057_ato_presidencial
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_repasse_estado_municipio"
down_revision: str | None = "0057_ato_presidencial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contas_municipio", sa.Column("transf_estado", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("contas_municipio", "transf_estado")
