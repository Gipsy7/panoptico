"""Pauta do Plenário da Câmara: sessões de hoje a +14 dias e as matérias de cada uma.

API: `/eventos?idOrgao=180` (Plenário) e `/eventos/{id}/pauta`. Armadilhas
(docs/FONTES_DE_DADOS.md): o item se repete uma vez por votação (mesma `ordem`, outro
`uriVotacao`), então a pauta é deduplicada por matéria dentro da sessão; e em MPV e em outras
matérias com parecer o `proposicao_` é o parecer (PAR/PEP, ano 0) e a matéria está em
`proposicaoRelacionada_`.
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import pauta_comum as pc

CASA = "camara"
FONTE = "camara_pauta"
ID_PLENARIO = 180
URL_EVENTOS = "https://dadosabertos.camara.leg.br/api/v2/eventos"
URL_PAUTA = "https://dadosabertos.camara.leg.br/api/v2/eventos/{id}/pauta"
URL_PAGINA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}"


def baixar(client: httpx.Client, hoje: date) -> dict[str, Any]:
    inicio, fim = pc.janela(hoje)
    eventos = comum.get_json(
        client,
        URL_EVENTOS,
        params={
            "idOrgao": ID_PLENARIO,
            "dataInicio": inicio.isoformat(),
            "dataFim": fim.isoformat(),
            "itens": 100,
        },
    )["dados"]
    sessoes = []
    for evento in eventos:
        pc.pausa()
        try:
            pauta = comum.get_json(client, URL_PAUTA.format(id=evento["id"]))["dados"]
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 404:
                raise
            pauta = []
        sessoes.append(
            {
                "id": evento["id"],
                "dataHoraInicio": evento["dataHoraInicio"],
                "descricaoTipo": evento.get("descricaoTipo"),
                "situacao": evento.get("situacao"),
                "pauta": pauta,
            }
        )
    return {"hoje": hoje.isoformat(), "sessoes": sessoes}


def _materia(item: dict[str, Any]) -> dict[str, Any] | None:
    """A matéria do item: a relacionada (MPV com parecer) ou a própria proposição."""
    materia = item.get("proposicaoRelacionada_") or item.get("proposicao_")
    return materia if materia and materia.get("id") else None


def _rotulo(item: dict[str, Any], materia: dict[str, Any]) -> str | None:
    if item.get("titulo"):
        return pc.limpar_texto(item["titulo"])
    if materia.get("siglaTipo") and materia.get("numero"):
        return f"{materia['siglaTipo']} {materia['numero']}/{materia.get('ano')}"
    return None


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    inicio, fim = pc.janela(date.fromisoformat(payload["hoje"]))
    itens: dict[tuple[str, str], dict[str, Any]] = {}
    for sessao in payload["sessoes"]:
        dia = date.fromisoformat(sessao["dataHoraInicio"][:10])
        if not inicio <= dia <= fim or (sessao.get("situacao") or "").startswith("Cancelad"):
            continue
        for item in sessao["pauta"]:
            materia = _materia(item)
            if materia is None:
                continue
            id_externo = str(materia["id"])
            chave = (str(sessao["id"]), id_externo)
            if chave in itens:  # repetição por votação
                continue
            itens[chave] = {
                "data": dia,
                "sessao": str(sessao["id"]),
                "ordem": item.get("ordem"),
                "proposicao": _rotulo(item, materia),
                "proposicao_id_externo": id_externo,
                "ementa": pc.limpar_texto(materia.get("ementa")) or None,
                "url": URL_PAGINA.format(id=id_externo),
            }
    return sorted(itens.values(), key=lambda i: (i["data"], i["sessao"], i["ordem"] or 0))


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    return pc.substituir_pauta(session, CASA, normalizar(payload), ingestao)


def executar(de_raw: Path | None = None, hoje: date | None = None) -> int:
    hoje = hoje or date.today()
    return comum.executar_ingestao(
        FONTE, URL_EVENTOS, lambda client: baixar(client, hoje), carregar, de_raw=de_raw
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} itens")
