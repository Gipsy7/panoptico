"""Proposições ampliadas, matéria das votações locais e índices de busca por ementa

Só aditiva: `proposicao.autor_descricao` e `proposicao.origem`; em `votacao_local`,
`materia_id_externo`, `materia_ementa` e `projeto_local_id` (FK opcional para `projeto_local`,
SET NULL); e índices GIN por expressão
`to_tsvector('portuguese', translate(lower(ementa), ...))` em `proposicao`,
`projeto_local` e `votacao_local.materia_ementa`. A expressão
normaliza acento com `translate(lower(...))` (IMMUTABLE), sem extensão nova, para a busca sem
acento ("saude mental" acha "saúde mental"). Sem
RECARREGAR_DADOS: as próximas cargas preenchem as colunas novas.

Revision ID: 0055_proposicao_ampliada
Revises: 0054_pauta_tramitacao
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0055_proposicao_ampliada"
down_revision: str | None = "0054_pauta_tramitacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mesma expressão de app/services/texto_busca.sql_tsvector (um teste compara os dois): minúsculas
# e sem acento, para "saude mental" achar "saúde mental". `translate` e `lower` são IMMUTABLE.
ACENTUADAS = "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ"
SEM_ACENTO = "aaaaaeeeeiiiiooooouuuucnaaaaaeeeeiiiiooooouuuucn"
EXPRESSAO = "to_tsvector('portuguese', translate(lower({coluna}), '{de}', '{para}'))"

INDICES_BUSCA = [
    ("ix_proposicao_ementa_busca", "proposicao", "ementa"),
    ("ix_projeto_local_ementa_busca", "projeto_local", "ementa"),
    ("ix_votacao_local_materia_ementa_busca", "votacao_local", "materia_ementa"),
]


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade() -> None:
    existentes = _colunas("proposicao")
    if "autor_descricao" not in existentes:
        op.add_column("proposicao", sa.Column("autor_descricao", sa.String(300), nullable=True))
    if "origem" not in existentes:
        op.add_column("proposicao", sa.Column("origem", sa.String(12), nullable=True))
    existentes = _colunas("votacao_local")
    if "materia_id_externo" not in existentes:
        op.add_column(
            "votacao_local", sa.Column("materia_id_externo", sa.String(40), nullable=True)
        )
    if "materia_ementa" not in existentes:
        op.add_column("votacao_local", sa.Column("materia_ementa", sa.Text(), nullable=True))
    if "projeto_local_id" not in existentes:
        op.add_column("votacao_local", sa.Column("projeto_local_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            op.f("fk_votacao_local_projeto_local_id_projeto_local"),
            "votacao_local",
            "projeto_local",
            ["projeto_local_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            op.f("ix_votacao_local_projeto_local_id"), "votacao_local", ["projeto_local_id"]
        )
    for nome, tabela, coluna in INDICES_BUSCA:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {nome} ON {tabela} "
            f"USING gin ({EXPRESSAO.format(coluna=coluna, de=ACENTUADAS, para=SEM_ACENTO)})"
        )


def downgrade() -> None:
    for nome, _, _ in INDICES_BUSCA:
        op.execute(f"DROP INDEX IF EXISTS {nome}")
    op.drop_index(op.f("ix_votacao_local_projeto_local_id"), table_name="votacao_local")
    op.drop_constraint(
        op.f("fk_votacao_local_projeto_local_id_projeto_local"),
        "votacao_local",
        type_="foreignkey",
    )
    op.drop_column("votacao_local", "projeto_local_id")
    op.drop_column("votacao_local", "materia_ementa")
    op.drop_column("votacao_local", "materia_id_externo")
    op.drop_column("proposicao", "origem")
    op.drop_column("proposicao", "autor_descricao")
