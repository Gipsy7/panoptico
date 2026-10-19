"""Orientação de partidos e blocos; resultado e placar oficial da votação (DECISOES, 2026-10-18)

Só aditiva, colunas opcionais:
- `orientacao.tipo` (lideranca, partido, bloco, federacao, outra) e `orientacao.partidos`
  (siglas que compõem o bloco ou a federação, quando a própria Câmara publica a composição).
  Linhas antigas ficam com `tipo` nulo e são lidas como lideranca (Governo, Maioria...).
- `votacao.resultado` (aprovada/rejeitada) e `votacao.placar_sim/nao/abstencao`, o placar
  como a fonte publica (inclusive nas votações secretas do Senado, que não têm voto nominal).

Não precisa de RECARREGAR_DADOS: a ingestão diária recarrega o ano corrente das votações
(apaga e reinsere), então 2026 se preenche sozinho. Anos anteriores, se desejado:
`python -m ingestion.camara.votacoes --ano 2025` e `python -m ingestion.senado.votacoes --ano 2025`.

Revision ID: 0045_orientacao_partidos
Revises: 0044_indice_pessoa_nome
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045_orientacao_partidos"
down_revision: str | None = "0044_indice_pessoa_nome"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orientacao", sa.Column("tipo", sa.String(length=12), nullable=True))
    op.add_column("orientacao", sa.Column("partidos", sa.Text(), nullable=True))
    op.add_column("votacao", sa.Column("resultado", sa.String(length=20), nullable=True))
    op.add_column("votacao", sa.Column("placar_sim", sa.Integer(), nullable=True))
    op.add_column("votacao", sa.Column("placar_nao", sa.Integer(), nullable=True))
    op.add_column("votacao", sa.Column("placar_abstencao", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("votacao", "placar_abstencao")
    op.drop_column("votacao", "placar_nao")
    op.drop_column("votacao", "placar_sim")
    op.drop_column("votacao", "resultado")
    op.drop_column("orientacao", "partidos")
    op.drop_column("orientacao", "tipo")
