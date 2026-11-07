"""Tipo de votação (mérito ou procedimento) nas votações nominais do Plenário (Frente 4)

Só acrescenta a coluna opcional `votacao.tipo_votacao` e um índice (nada é alterado nem removido)
e preenche as votações já gravadas com a regra de app/services/tipo_votacao.py, a mesma que a
carga aplica daqui em diante. Sem RECARREGAR_DADOS: o preenchimento é feito aqui, em lotes.

Revision ID: 0063_tipo_votacao
Revises: 0061_sugestoes_correcoes
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0063_tipo_votacao"
down_revision: str | None = "0062_normas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A regra mora no código da aplicação de propósito: migração e carga usam a mesma.
    from app.services.tipo_votacao import classificar

    op.add_column("votacao", sa.Column("tipo_votacao", sa.String(length=12), nullable=True))
    op.create_index("ix_votacao_casa_tipo_data", "votacao", ["casa", "tipo_votacao", "data"])

    conexao = op.get_bind()
    linhas = conexao.execute(sa.text("select id, descricao from votacao")).all()
    por_tipo: dict[str, list[int]] = {}
    for id_, descricao in linhas:
        por_tipo.setdefault(classificar(descricao), []).append(id_)
    for tipo, ids in por_tipo.items():
        for inicio in range(0, len(ids), 5000):
            conexao.execute(
                sa.text("update votacao set tipo_votacao = :tipo where id = any(:ids)"),
                {"tipo": tipo, "ids": ids[inicio : inicio + 5000]},
            )


def downgrade() -> None:
    op.drop_index("ix_votacao_casa_tipo_data", table_name="votacao")
    op.drop_column("votacao", "tipo_votacao")
