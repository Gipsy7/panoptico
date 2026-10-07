"""Regras comuns às votações nominais de Plenário das duas casas."""

from typing import Any

from sqlalchemy import delete, extract
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Votacao, Voto


def recarregar_votacoes(
    session: Session,
    casa: str,
    ano: int,
    votacoes: list[dict[str, Any]],
    votos: list[dict[str, Any]],
    ingestao: FonteIngestao,
) -> int:
    """Substitui as votações (e votos) de uma casa num ano.

    `votos` usa `id_externo_votacao` e `parlamentar_id`; o id interno da votação é
    resolvido aqui depois da inserção.
    """
    if not votacoes:
        raise ValueError(f"Nenhuma votação de {casa} em {ano}; abortando para não zerar o ano.")
    session.execute(
        delete(Votacao).where(Votacao.casa == casa, extract("year", Votacao.data) == ano)
    )
    mapa: dict[str, int] = {}
    for inicio in range(0, len(votacoes), 2000):
        lote = [
            {**v, "casa": casa, "ingestao_id": ingestao.id}
            for v in votacoes[inicio : inicio + 2000]
        ]
        resultado = session.execute(
            insert(Votacao).values(lote).returning(Votacao.id_externo, Votacao.id)
        )
        mapa.update({id_externo: id_ for id_externo, id_ in resultado})

    linhas = {
        (mapa[v["id_externo_votacao"]], v["parlamentar_id"]): {
            "votacao_id": mapa[v["id_externo_votacao"]],
            "parlamentar_id": v["parlamentar_id"],
            "voto": v["voto"],
        }
        for v in votos
        if v["id_externo_votacao"] in mapa
    }
    valores = list(linhas.values())
    for inicio in range(0, len(valores), 5000):
        session.execute(insert(Voto).values(valores[inicio : inicio + 5000]))
    return len(valores)
