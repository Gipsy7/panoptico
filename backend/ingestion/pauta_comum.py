"""Peças comuns da pauta do Plenário e da tramitação das proposições (Câmara e Senado).

Recorte da tramitação (docs/DECISOES.md, 2026-10-21): proposições com votação nominal no
ano atual e no anterior, mais as que estão na pauta. `--todas` (só no acervo) acrescenta
as proposições da tabela `proposicao`. A carga é incremental: a proposição só é buscada de
novo quando a "marca" da fonte (última movimentação) mudou desde a última carga.
"""

import time
from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy import insert as sa_insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PautaItem, Proposicao, Tramitacao, Votacao

JANELA_DIAS = 14
# Pausa educada entre chamadas à API da Casa (segundos).
PAUSA = 0.3
LOTE = 2000


def pausa() -> None:
    time.sleep(PAUSA)


def limpar_texto(texto: str | None) -> str:
    return " ".join((texto or "").split())


def janela(hoje: date) -> tuple[date, date]:
    return hoje, hoje + timedelta(days=JANELA_DIAS)


def substituir_pauta(
    session: Session, casa: str, itens: list[dict[str, Any]], ingestao: FonteIngestao
) -> int:
    """Recarga integral: a pauta da casa é só a janela de hoje a +14 dias, então tudo que
    estava antes (inclusive sessões já passadas) sai. Janela vazia é legítima (recesso,
    período eleitoral): não aborta."""
    session.execute(delete(PautaItem).where(PautaItem.casa == casa))
    for inicio in range(0, len(itens), LOTE):
        lote = [
            {**item, "casa": casa, "ingestao_id": ingestao.id}
            for item in itens[inicio : inicio + LOTE]
        ]
        session.execute(sa_insert(PautaItem), lote)
    return len(itens)


def ids_do_recorte(session: Session, casa: str, hoje: date, todas: bool = False) -> list[str]:
    """Proposições (id na fonte) com votação nominal no ano anterior e no atual, as da pauta
    e, com `todas`, as da tabela `proposicao` (PL, PLP, PEC e PDL desde 2023)."""
    desde = date(hoje.year - 1, 1, 1)
    ids = set(
        session.scalars(
            select(Votacao.proposicao_id_externo)
            .where(
                Votacao.casa == casa,
                Votacao.data >= desde,
                Votacao.proposicao_id_externo.is_not(None),
            )
            .distinct()
        )
    )
    ids |= set(
        session.scalars(
            select(PautaItem.proposicao_id_externo)
            .where(PautaItem.casa == casa, PautaItem.proposicao_id_externo.is_not(None))
            .distinct()
        )
    )
    if todas:
        ids |= set(session.scalars(select(Proposicao.id_externo).where(Proposicao.casa == casa)))
    return sorted(ids, key=lambda i: (len(i), i))


def marcas_atuais(session: Session, casa: str) -> dict[str, str]:
    """id da proposição -> marca da fonte guardada na última carga."""
    linhas = session.execute(
        select(Tramitacao.proposicao_id_externo, func.max(Tramitacao.fonte_marca))
        .where(Tramitacao.casa == casa, Tramitacao.fonte_marca.is_not(None))
        .group_by(Tramitacao.proposicao_id_externo)
    )
    return {id_externo: marca for id_externo, marca in linhas}


def substituir_tramitacoes(
    session: Session,
    casa: str,
    por_proposicao: dict[str, list[dict[str, Any]]],
    ingestao: FonteIngestao,
) -> int:
    """Por proposição, apaga e reinsere as linhas (a fonte pode corrigir o passado)."""
    ids = list(por_proposicao)
    for inicio in range(0, len(ids), LOTE):
        session.execute(
            delete(Tramitacao).where(
                Tramitacao.casa == casa,
                Tramitacao.proposicao_id_externo.in_(ids[inicio : inicio + LOTE]),
            )
        )
    linhas = [
        {**linha, "casa": casa, "proposicao_id_externo": id_externo, "ingestao_id": ingestao.id}
        for id_externo, do_projeto in por_proposicao.items()
        for linha in do_projeto
    ]
    for inicio in range(0, len(linhas), 5000):
        session.execute(sa_insert(Tramitacao), linhas[inicio : inicio + 5000])
    return len(linhas)


def aplicar_relatores(
    session: Session,
    casa: str,
    relatores: dict[str, tuple[str | None, str | None]],
    mapa: dict[str, int],
) -> int:
    """Grava `relator` e `relator_parlamentar_id` nas proposições que já temos.
    `relatores`: id da proposição -> (nome, id do parlamentar na fonte); `mapa`: id na fonte
    -> id interno (comum.mapa_parlamentares)."""
    atualizadas = 0
    for id_externo, (nome, id_parlamentar) in relatores.items():
        resultado = session.execute(
            update(Proposicao)
            .where(Proposicao.casa == casa, Proposicao.id_externo == id_externo)
            .values(
                relator=nome or None,
                relator_parlamentar_id=mapa.get(id_parlamentar) if id_parlamentar else None,
            )
        )
        atualizadas += resultado.rowcount
    return atualizadas
