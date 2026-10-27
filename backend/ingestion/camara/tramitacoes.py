"""Tramitação das proposições da Câmara (API por proposição) e o último relator.

Por proposição do recorte (votação nominal no ano atual e no anterior, mais a pauta; `--todas`
acrescenta tudo da tabela `proposicao`): a ficha `/proposicoes/{id}` traz o último status
(`dataHora`, `sequencia`, `uriUltimoRelator`) e `/proposicoes/{id}/tramitacoes` as linhas. A
ficha é a "sonda" do incremental: só se busca a tramitação quando data e sequência do status
mudaram desde a última carga. NÃO se usa o arquivo em lote `proposicoesTramitacoes-{ano}.csv`,
que não bate com a API (docs/FONTES_DE_DADOS.md).

`sequencia` tem buracos, então a ordem gravada é a posição por (data, sequência). A descrição
é o `despacho` (o texto que explica); quando falta, a `descricaoTramitacao`.
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

CASA = "camara"
FONTE = "camara_tramitacoes"
URL = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}"
URL_DEPUTADO = "https://dadosabertos.camara.leg.br/api/v2/deputados/{id}"


def marca_do_status(status: dict[str, Any]) -> str:
    return f"{status.get('dataHora')}#{status.get('sequencia')}"


def _get_ou_none(client: httpx.Client, url: str) -> Any | None:
    pc.pausa()
    try:
        return comum.get_json(client, url)["dados"]
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code == 404:
            return None
        raise


def baixar(client: httpx.Client, ids: list[str], marcas: dict[str, str]) -> dict[str, Any]:
    proposicoes: dict[str, Any] = {}
    nomes_de_relatores: dict[str, str | None] = {}
    inalteradas = 0
    sem_ficha = []
    for id_externo in ids:
        ficha = _get_ou_none(client, URL.format(id=id_externo))
        status = (ficha or {}).get("statusProposicao")
        if not status:
            sem_ficha.append(id_externo)
            continue
        if marcas.get(id_externo) == marca_do_status(status):
            inalteradas += 1
            continue
        relator_id = (status.get("uriUltimoRelator") or "").rstrip("/").rsplit("/", 1)[-1] or None
        if relator_id and relator_id not in nomes_de_relatores:
            deputado = _get_ou_none(client, URL_DEPUTADO.format(id=relator_id)) or {}
            ultimo = deputado.get("ultimoStatus") or {}
            nomes_de_relatores[relator_id] = ultimo.get("nomeEleitoral") or ultimo.get("nome")
        proposicoes[id_externo] = {
            "ficha": {
                k: ficha.get(k) for k in ("id", "siglaTipo", "numero", "ano", "statusProposicao")
            },
            "relator": {"id": relator_id, "nome": nomes_de_relatores.get(relator_id)}
            if relator_id
            else None,
            "tramitacoes": _get_ou_none(client, URL.format(id=id_externo) + "/tramitacoes") or [],
        }
    return {
        "recorte": len(ids),
        "inalteradas": inalteradas,
        "sem_ficha": sem_ficha,
        "proposicoes": proposicoes,
    }


def normalizar(registro: dict[str, Any]) -> list[dict[str, Any]]:
    """Linhas de uma proposição, em ordem cronológica, já com a marca da fonte."""
    marca = marca_do_status(registro["ficha"]["statusProposicao"])
    bruto = sorted(registro["tramitacoes"], key=lambda t: (t["dataHora"], t.get("sequencia") or 0))
    return [
        {
            "ordem": ordem,
            "data": datetime.fromisoformat(t["dataHora"]),
            "orgao": t.get("siglaOrgao"),
            "tipo": pc.limpar_texto(t.get("descricaoTramitacao")) or None,
            "descricao": pc.limpar_texto(t.get("despacho"))
            or pc.limpar_texto(t.get("descricaoTramitacao")),
            "situacao": pc.limpar_texto(t.get("descricaoSituacao")) or None,
            "fonte_marca": marca,
        }
        for ordem, t in enumerate(bruto, start=1)
    ]


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    por_proposicao = {i: normalizar(r) for i, r in payload["proposicoes"].items()}
    total = pc.substituir_tramitacoes(session, CASA, por_proposicao, ingestao)
    relatores = {
        i: ((r["relator"] or {}).get("nome"), (r["relator"] or {}).get("id"))
        for i, r in payload["proposicoes"].items()
    }
    pc.aplicar_relatores(session, CASA, relatores, comum.mapa_parlamentares(session, CASA))
    ingestao.total_fonte = payload["recorte"]
    if payload["sem_ficha"]:
        ingestao.alertas = [
            f"{len(payload['sem_ficha'])} proposições do recorte sem ficha na API "
            f"(ex.: {', '.join(payload['sem_ficha'][:3])})"
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
