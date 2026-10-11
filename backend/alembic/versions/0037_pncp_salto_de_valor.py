"""PNCP: salto de valor (global acima de 100 vezes o inicial) também é valor suspeito

Só dados: reavalia `pncp_contrato.valor_suspeito` com a regra nova de
`ingestion/pncp/suspeito.py` (valor inicial positivo e global maior que 100 vezes ele; mais o
termo conhecido de Campinas). Não desmarca ninguém.

Revision ID: 0037_pncp_salto_de_valor
Revises: 0036_pncp_ente_publico
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0037_pncp_salto_de_valor"
down_revision: str | None = "0036_pncp_ente_publico"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE pncp_contrato SET valor_suspeito = true
        WHERE NOT valor_suspeito AND (
            (valor_inicial > 0 AND valor_global > valor_inicial * 100)
            OR numero_controle = '51885242000140-2-000286/2026')
        """
    )


def downgrade() -> None:
    pass  # a marcação é derivada do valor; não há o que desfazer
