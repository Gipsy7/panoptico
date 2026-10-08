"""Regras comuns às votações nominais de Plenário das duas casas."""

from typing import Any

from sqlalchemy import delete, extract
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Orientacao, Votacao, VotacaoComissao, Voto, VotoComissao

# Só estas bancadas têm nome estável; os blocos vêm truncados ("Bl UniPpPsd...").
BANCADAS = {"Governo", "Maioria", "Minoria", "Oposição"}


def recarregar_votacoes(
    session: Session,
    casa: str,
    ano: int,
    votacoes: list[dict[str, Any]],
    votos: list[dict[str, Any]],
    ingestao: FonteIngestao,
    orientacoes: list[dict[str, Any]] | None = None,
) -> int:
    """Substitui as votações (votos e orientações) de uma casa num ano.

    `votos` e `orientacoes` usam `id_externo_votacao`; o id interno da votação é
    resolvido aqui depois da inserção. Votos levam `parlamentar_id`, `voto` e,
    opcionalmente, `partido`.
    """
    if not votacoes:
        raise ValueError(f"Nenhuma votação de {casa} em {ano}; abortando para não zerar o ano.")
    session.execute(
        delete(Votacao).where(Votacao.casa == casa, extract("year", Votacao.data) == ano)
    )
    mapa: dict[str, int] = {}
    for inicio in range(0, len(votacoes), 2000):
        lote = [
            {"proposicao_id_externo": None, "proposicao_ementa": None, **v}
            | {"casa": casa, "ingestao_id": ingestao.id}
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
            "partido": v.get("partido"),
        }
        for v in votos
        if v["id_externo_votacao"] in mapa
    }
    valores = list(linhas.values())
    for inicio in range(0, len(valores), 5000):
        session.execute(insert(Voto).values(valores[inicio : inicio + 5000]))

    orientacoes_validas = {
        (mapa[o["id_externo_votacao"]], o["bancada"]): {
            "votacao_id": mapa[o["id_externo_votacao"]],
            "bancada": o["bancada"],
            "orientacao": o["orientacao"],
        }
        for o in orientacoes or []
        if o["id_externo_votacao"] in mapa and o["bancada"] in BANCADAS
    }
    if orientacoes_validas:
        session.execute(insert(Orientacao).values(list(orientacoes_validas.values())))
    return len(valores)


def recarregar_comissoes(
    session: Session,
    casa: str,
    ano: int,
    votacoes: list[dict[str, Any]],
    votos: list[dict[str, Any]],
    ingestao: FonteIngestao,
) -> int:
    """Substitui as votações nominais de comissões de uma casa num ano. Ao contrário do
    Plenário, um ano sem votação nominal em comissão é possível: lista vazia só limpa."""
    session.execute(
        delete(VotacaoComissao).where(
            VotacaoComissao.casa == casa, extract("year", VotacaoComissao.data) == ano
        )
    )
    if not votacoes:
        return 0
    mapa: dict[str, int] = {}
    for inicio in range(0, len(votacoes), 2000):
        lote = [
            {"orgao_nome": None, "proposicao": None, "proposicao_id_externo": None,
             "proposicao_ementa": None, **v}
            | {"casa": casa, "ingestao_id": ingestao.id}
            for v in votacoes[inicio : inicio + 2000]
        ]  # fmt: skip
        resultado = session.execute(
            insert(VotacaoComissao)
            .values(lote)
            .returning(VotacaoComissao.id_externo, VotacaoComissao.id)
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
        session.execute(insert(VotoComissao).values(valores[inicio : inicio + 5000]))
    return len(valores)
