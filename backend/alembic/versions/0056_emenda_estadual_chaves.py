"""Emendas estaduais de várias UFs: chaves mais longas

Só alarga colunas de texto de `emenda_estadual` (`codigo`, `proposta` e `transferencia`, de
20 para 60 caracteres): a Bahia identifica a emenda pela dotação
("2022.3.26.26601.305.5112.500070.5", 33 caracteres) e Pernambuco pela emenda com o empenho.
Nada é removido nem reescrito (no Postgres, aumentar o limite de um varchar não reescreve a
tabela); o código antigo continua funcionando. Sem RECARREGAR_DADOS: cada UF tem carga própria.

Revision ID: 0056_emenda_estadual_chaves
Revises: 0055_proposicao_ampliada
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0056_emenda_estadual_chaves"
down_revision: str | None = "0055_proposicao_ampliada"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUNAS = ("codigo", "proposta", "transferencia")


def upgrade() -> None:
    for coluna in COLUNAS:
        op.alter_column(
            "emenda_estadual",
            coluna,
            existing_type=sa.String(length=20),
            type_=sa.String(length=60),
            existing_nullable=coluna == "transferencia",
        )


def downgrade() -> None:
    for coluna in COLUNAS:
        op.alter_column(
            "emenda_estadual",
            coluna,
            existing_type=sa.String(length=60),
            type_=sa.String(length=20),
            existing_nullable=coluna == "transferencia",
        )
