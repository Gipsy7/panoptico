"""Tramitação das matérias no Senado (API de processos) e o último relator.

O id da matéria que o resto do projeto usa (`votacao.proposicao_id_externo` e
`proposicao.id_externo`) é o `codigoMateria`; a API de tramitação usa o `idProcesso`. A ponte é
`/processo?codigoMateria=` (uma chamada, devolve o processo e `dataUltimaAtualizacao`), que
também é a "sonda" do incremental: só se baixa `/processo/{id}` e `/processo/relatoria` quando
essa data mudou desde a última carga. Recorte como o da Câmara (`--todas` só no acervo).

Cada informe legislativo (`autuacoes[].informesLegislativos[]`) vira uma linha: data, colegiado,
texto. A situação da linha é a situação do processo vigente na data do informe.
"""

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import pauta_comum as pc

CASA = "senado"
FONTE = "senado_tramitacoes"
URL = "https://legis.senado.leg.br/dadosabertos/processo"
URL_RELATORIA = URL + "/relatoria"


def _get_ou_none(client: httpx.Client, url: str, params: dict | None = None) -> Any | None:
    pc.pausa()
    try:
        return comum.get_json(client, url, params=params)
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code == 404:
            return None
        raise


def baixar(client: httpx.Client, ids: list[str], marcas: dict[str, str]) -> dict[str, Any]:
    materias: dict[str, Any] = {}
    inalteradas = 0
    sem_processo = []
    for codigo in ids:
        achados = _get_ou_none(client, URL, {"codigoMateria": codigo}) or []
        lista = next((p for p in achados if str(p.get("codigoMateria")) == codigo), None)
        if lista is None:
            sem_processo.append(codigo)
            continue
        marca = lista.get("dataUltimaAtualizacao")
        # Sem data de atualização na lista (acontece, ex.: PEC 81/2015) não há sonda: rebusca.
        if marca and marcas.get(codigo) == marca:
            inalteradas += 1
            continue
        processo = _get_ou_none(client, f"{URL}/{lista['id']}")
        if processo is None:
            sem_processo.append(codigo)
            continue
        materias[codigo] = {
            "marca": marca,
            "processo": processo,
            "relatoria": _get_ou_none(client, URL_RELATORIA, {"idProcesso": lista["id"]}) or [],
        }
    return {
        "recorte": len(ids),
        "inalteradas": inalteradas,
        "sem_processo": sem_processo,
        "materias": materias,
    }


def _situacao_na_data(situacoes: list[dict[str, Any]], dia: date) -> str | None:
    """Situação do processo vigente na data (a mais recente que já tinha começado)."""
    vigentes = [
        s
        for s in situacoes
        if s.get("inicio")
        and date.fromisoformat(s["inicio"][:10]) <= dia
        and (not s.get("fim") or dia <= date.fromisoformat(s["fim"][:10]))
    ]
    if not vigentes:
        return None
    return pc.limpar_texto(max(vigentes, key=lambda s: s["inicio"]).get("descricao")) or None


def normalizar(registro: dict[str, Any]) -> list[dict[str, Any]]:
    """Informes de todas as autuações, em ordem cronológica, com a marca da fonte."""
    bruto = []
    for autuacao in registro["processo"].get("autuacoes") or []:
        situacoes = autuacao.get("situacoes") or []
        for informe in autuacao.get("informesLegislativos") or []:
            if not informe.get("data"):
                continue
            quando = datetime.fromisoformat(informe["data"])
            bruto.append((quando, informe.get("id") or 0, informe, situacoes))
    bruto.sort(key=lambda x: (x[0], x[1]))
    return [
        {
            "ordem": ordem,
            "data": quando,
            "orgao": ((informe.get("colegiado") or {}).get("sigla")),
            "tipo": None,
            "descricao": pc.limpar_texto(informe.get("descricao")),
            "situacao": _situacao_na_data(situacoes, quando.date()),
            "fonte_marca": registro["marca"],
        }
        for ordem, (quando, _, informe, situacoes) in enumerate(bruto, start=1)
    ]


def ultimo_relator(relatoria: list[dict[str, Any]]) -> tuple[str, str | None] | None:
    """(nome, codigo do senador) da designação mais recente, mesmo já encerrada."""
    if not relatoria:
        return None
    recente = max(relatoria, key=lambda r: r.get("dataDesignacao") or "")
    codigo = recente.get("codigoParlamentar")
    return recente.get("nomeParlamentar"), str(codigo) if codigo else None


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    por_proposicao = {c: normalizar(r) for c, r in payload["materias"].items()}
    total = pc.substituir_tramitacoes(session, CASA, por_proposicao, ingestao)
    relatores = {
        c: ultimo_relator(r["relatoria"]) or (None, None) for c, r in payload["materias"].items()
    }
    pc.aplicar_relatores(session, CASA, relatores, comum.mapa_parlamentares(session, CASA))
    ingestao.total_fonte = payload["recorte"]
    if payload["sem_processo"]:
        ingestao.alertas = [
            f"{len(payload['sem_processo'])} matérias do recorte sem processo na API "
            f"(ex.: {', '.join(payload['sem_processo'][:3])})"
        ]
    return total


def executar(todas: bool = False, de_raw: Path | None = None, hoje: date | None = None) -> int:
    hoje = hoje or date.today()

    def baixar_recorte(client: httpx.Client) -> dict[str, Any]:
        with comum.SessionLocal() as session:
            ids = pc.ids_do_recorte(session, CASA, hoje, todas)
            marcas = pc.marcas_atuais(session, CASA)
        return baixar(client, ids, marcas)

    return comum.executar_ingestao(FONTE, URL, baixar_recorte, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    parser.add_argument(
        "--todas",
        action="store_true",
        help="Recorte do acervo: também todas as proposições da tabela proposicao (milhares de "
        "chamadas; não usar na produção)",
    )
    args = parser.parse_args()
    print(f"{FONTE}: {executar(todas=args.todas, de_raw=args.de_raw)} linhas")
