"""Regras comuns às proposições das duas casas."""

from datetime import date
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Autoria, FonteIngestao, Proposicao

# Só o que é legislação de fato; requerimentos, pareceres e emendas ficam de fora.
TIPOS = {"PL", "PLP", "PEC", "PDL"}
INICIO_LEGISLATURA = date(2023, 2, 1)


def virou_lei(situacao: str | None) -> bool:
    # "Transformada em norma jurídica" (com ou sem veto). "Transformado em nova
    # proposição" não é lei: o texto seguiu em outra proposição.
    return "norma jur" in (situacao or "").lower()


def upsert_proposicoes(
    session: Session, casa: str, registros: list[dict[str, Any]], ingestao: FonteIngestao
) -> dict[str, int]:
    """Insere ou atualiza as proposições e devolve id_externo -> id interno."""
    mapa: dict[str, int] = {}
    for inicio in range(0, len(registros), 2000):
        lote = [
            {**r, "casa": casa, "ingestao_id": ingestao.id}
            for r in registros[inicio : inicio + 2000]
        ]
        stmt = insert(Proposicao).values(lote)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_proposicao_casa_id_externo",
            set_={c: stmt.excluded[c] for c in lote[0] if c not in ("casa", "id_externo")},
        ).returning(Proposicao.id_externo, Proposicao.id)
        mapa.update({id_externo: id_ for id_externo, id_ in session.execute(stmt)})
    return mapa


def substituir_autorias(
    session: Session, proposicao_ids: list[int], autorias: list[dict[str, Any]]
) -> int:
    """Troca as autorias das proposições informadas pelas da carga atual."""
    for inicio in range(0, len(proposicao_ids), 5000):
        session.execute(
            delete(Autoria).where(Autoria.proposicao_id.in_(proposicao_ids[inicio : inicio + 5000]))
        )
    unicas = {(a["proposicao_id"], a["parlamentar_id"]): a for a in autorias}
    linhas = list(unicas.values())
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(Autoria).values(linhas[inicio : inicio + 5000]))
    return len(linhas)
