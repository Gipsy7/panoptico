"""Temas oficiais das matérias do Senado (classificação do próprio Senado).

Cada processo tem uma ou mais classificações hierárquicas, por exemplo
"Política Social / Educação / Educação Básica". Usamos o 2º nível ("Educação"), que
tem granularidade parecida com os temas da Câmara; se só houver o 1º, usamos ele.
Homenagens ("Honorífico" / "Homenagem") recebem o mesmo rótulo usado na Câmara, para
que a exclusão das homenagens nas contagens valha igual nas duas casas.

A classificação só vem no detalhe de cada processo (duas chamadas por matéria: a busca
pelo código da matéria e o detalhe). Por isso a carga é incremental: só busca as
matérias do Senado (apresentadas ou votadas) que ainda não têm tema. Use --tudo para
refazer todas.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, Proposicao, ProposicaoTema, Votacao
from ingestion import comum
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO, TEMA_HOMENAGENS

FONTE = "senado_temas"
CASA = "senado"
URL_BUSCA = "https://legis.senado.leg.br/dadosabertos/processo"
URL_DETALHE = "https://legis.senado.leg.br/dadosabertos/processo/{id}"


def _materias(session: Session) -> set[str]:
    apresentadas = session.scalars(select(Proposicao.id_externo).where(Proposicao.casa == CASA))
    votadas = session.scalars(
        select(Votacao.proposicao_id_externo).where(
            Votacao.casa == CASA, Votacao.proposicao_id_externo.is_not(None)
        )
    )
    return set(apresentadas) | set(votadas)


def _ja_classificadas(session: Session) -> set[str]:
    return set(
        session.scalars(
            select(ProposicaoTema.proposicao_id_externo)
            .where(ProposicaoTema.casa == CASA)
            .distinct()
        )
    )


def _classificacoes(client: httpx.Client, codigo_materia: str) -> list[dict] | None:
    """Classificações da matéria; None se a consulta falhar (fica para a próxima carga)."""
    try:
        processos = comum.get_json(
            client, URL_BUSCA, params={"codigoMateria": codigo_materia}, tentativas=5
        )
        if not processos:
            return []
        detalhe = comum.get_json(client, URL_DETALHE.format(id=processos[0]["id"]), tentativas=5)
    except httpx.HTTPError:
        return None
    return detalhe.get("classificacoes") or []


def baixar(client: httpx.Client, tudo: bool = False) -> dict[str, list[dict]]:
    with SessionLocal() as session:
        faltando = _materias(session) - (set() if tudo else _ja_classificadas(session))
    faltando = sorted(faltando)
    # A API do Senado limita a taxa (429): poucas conexões em paralelo.
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = pool.map(lambda c: _classificacoes(client, c), faltando)
        respostas = dict(zip(faltando, resultados, strict=True))
    falhas = sum(1 for r in respostas.values() if r is None)
    if falhas:
        print(f"  matérias sem resposta (ficam para a próxima carga): {falhas}")
    return {codigo: r for codigo, r in respostas.items() if r is not None}


def tema_da_classificacao(hierarquia: str) -> str:
    """'Política Social / Educação / Educação Básica' -> 'Educação'."""
    niveis = [n.strip() for n in hierarquia.split("/") if n.strip()]
    if not niveis:
        return SEM_CLASSIFICACAO
    if niveis[0] == "Honorífico" or "Homenagem" in niveis:
        return TEMA_HOMENAGENS
    return niveis[1] if len(niveis) > 1 else niveis[0]


def normalizar(payload: dict[str, list[dict]]) -> list[dict[str, Any]]:
    registros = set()
    for codigo, classificacoes in payload.items():
        temas = {tema_da_classificacao(c.get("descricaoHierarquia") or "") for c in classificacoes}
        # Matéria sem classificação fica registrada para não ser buscada de novo todo dia.
        for tema in temas or {SEM_CLASSIFICACAO}:
            registros.add((codigo, tema))
    return [
        {"casa": CASA, "proposicao_id_externo": codigo, "tema": tema}
        for codigo, tema in sorted(registros)
    ]


def carregar(session: Session, payload: dict, ingestao: FonteIngestao, tudo: bool = False) -> int:
    registros = normalizar(payload)
    if tudo:
        session.execute(delete(ProposicaoTema).where(ProposicaoTema.casa == CASA))
    for inicio in range(0, len(registros), 5000):
        lote = registros[inicio : inicio + 5000]
        session.execute(insert(ProposicaoTema).values(lote).on_conflict_do_nothing())
    return len(registros)


def executar(de_raw: Path | None = None, tudo: bool = False) -> int:
    return comum.executar_ingestao(
        FONTE,
        URL_DETALHE.format(id="{id}"),
        lambda client: baixar(client, tudo),
        lambda session, payload, ingestao: carregar(session, payload, ingestao, tudo),
        de_raw=de_raw,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    parser.add_argument("--tudo", action="store_true", help="Busca de novo todas as matérias")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw, tudo=args.tudo)} temas")
