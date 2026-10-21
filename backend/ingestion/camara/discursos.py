"""Discursos em Plenário da Câmara dos Deputados (API por deputado).

`GET /deputados/{id}/discursos` traz o id do orador (vínculo forte, sem casar nome), a fase da
sessão, o tipo do discurso, o sumário oficial e o link do Diário. A transcrição (~3 KB por
discurso) não é guardada nem no bruto. Não há id de discurso: a chave é
"<deputado>:<data e hora>:<ocorrência>". Não há ligação direta com a votação (`uriEvento` vem
vazio): o sumário cita a matéria por extenso e o discurso é ligado ao projeto votado no mesmo dia
(`ingestion/discursos_comum.py`).

Carga incremental: da última carga `ok` menos 7 dias (a Câmara indexa com atraso) até hoje; a
primeira carga vai do início do ano anterior. O bruto guarda a janela, então `--de-raw` repete a
mesma carga sem rede. A carga apaga e reinsere os discursos da janela.
"""

import argparse
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import discursos_comum as dc

FONTE = "camara_discursos"
CASA = "camara"
API = "https://dadosabertos.camara.leg.br/api/v2"
URL = API + "/deputados/{id}/discursos"
MARGEM_DIAS = 7
PAUSA = 0.3  # segundos entre chamadas (cortesia com a API)
CAMPOS = ("dataHoraInicio", "tipoDiscurso", "urlTexto", "urlVideo", "keywords", "sumario")


def _enxuto(d: dict[str, Any]) -> dict[str, Any]:
    """O bruto guarda o discurso sem a transcrição."""
    resumo = {c: d.get(c) for c in CAMPOS}
    resumo["fase"] = (d.get("faseEvento") or {}).get("titulo")
    return resumo


def baixar_deputado(client: httpx.Client, id_deputado: str, inicio: date, fim: date) -> list:
    discursos, pagina = [], 1
    while True:
        resposta = comum.get_json(
            client,
            URL.format(id=id_deputado),
            params={
                "dataInicio": inicio.isoformat(),
                "dataFim": fim.isoformat(),
                "itens": 100,
                "pagina": pagina,
                "ordenarPor": "dataHoraInicio",
                "ordem": "ASC",
            },
        )
        discursos += [_enxuto(d) for d in resposta.get("dados", [])]
        if not any(link.get("rel") == "next" for link in resposta.get("links", [])):
            return discursos
        pagina += 1
        time.sleep(PAUSA)


def baixar(
    client: httpx.Client, ids: list[str], inicio: date, fim: date, completa: bool
) -> dict[str, Any]:
    deputados = {}
    for id_deputado in ids:
        discursos = baixar_deputado(client, id_deputado, inicio, fim)
        if discursos:
            deputados[id_deputado] = discursos
        time.sleep(PAUSA)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "completa": completa,
        "deputados": deputados,
    }


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Bruto -> discursos com o id externo do deputado e as matérias citadas."""
    registros = []
    for id_deputado, discursos in payload["deputados"].items():
        ocorrencia: dict[str, int] = {}
        for d in discursos:
            instante = d.get("dataHoraInicio") or ""
            if len(instante) < 10:
                continue
            n = ocorrencia[instante] = ocorrencia.get(instante, 0) + 1
            sumario = " ".join((d.get("sumario") or "").split()) or None
            registros.append(
                {
                    "id_externo": f"{id_deputado}:{instante}:{n}",
                    "id_externo_parlamentar": id_deputado,
                    "data": date.fromisoformat(instante[:10]),
                    "data_hora": dc.hora(instante),
                    "sessao_id_externo": None,
                    "fase": d.get("fase") or (d.get("faseEvento") or {}).get("titulo"),
                    "tipo": d.get("tipoDiscurso"),
                    "sumario": sumario,
                    "url_texto": d.get("urlTexto") or None,
                    "url_video": d.get("urlVideo") or None,
                    "citadas": dc.citacoes(f"{sumario or ''} {d.get('keywords') or ''}"),
                }
            )
    return registros


def carregar(session: Session, payload: dict[str, Any], ingestao: FonteIngestao) -> int:
    linhas = comum.vincular_parlamentares(session, CASA, normalizar(payload))
    return dc.recarregar_discursos(
        session,
        CASA,
        date.fromisoformat(payload["inicio"]),
        date.fromisoformat(payload["fim"]),
        linhas,
        ingestao,
        completa=payload.get("completa", False),
    )


def executar(de_raw: Path | None = None, desde: date | None = None) -> int:
    """Incremental por padrão; `desde` força o início da janela (carga completa se antes do
    ano anterior ao atual)."""
    hoje = date.today()
    piso = date(comum.anos_padrao()[0], 1, 1)
    estado: dict[str, Any] = {}
    if de_raw is None:
        with comum.SessionLocal() as session:
            if desde is not None:
                inicio, completa = max(desde, piso), desde <= piso
            else:
                inicio, completa = dc.inicio_incremental(session, FONTE, MARGEM_DIAS, piso, hoje)
            estado = {
                "inicio": inicio,
                "completa": completa,
                "ids": sorted(comum.mapa_parlamentares(session, CASA)),
            }

    def baixar_janela(client: httpx.Client) -> dict[str, Any]:
        return baixar(client, estado["ids"], estado["inicio"], hoje, estado["completa"])

    return comum.executar_ingestao(
        FONTE, URL, baixar_janela, carregar, de_raw=de_raw, extensao_raw=".json"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    parser.add_argument(
        "--desde",
        type=date.fromisoformat,
        help="Início da janela (AAAA-MM-DD); padrão: incremental",
    )
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw, desde=args.desde)} discursos")
