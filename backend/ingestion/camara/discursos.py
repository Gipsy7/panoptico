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
from datetime import date, timedelta
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
TENTATIVAS_MES = 2  # o pedido do mês inteiro ainda tenta de novo (falha passageira de rede)
CAMPOS = ("dataHoraInicio", "tipoDiscurso", "urlTexto", "urlVideo", "keywords", "sumario")


def _enxuto(d: dict[str, Any]) -> dict[str, Any]:
    """O bruto guarda o discurso sem a transcrição."""
    resumo = {c: d.get(c) for c in CAMPOS}
    resumo["fase"] = (d.get("faseEvento") or {}).get("titulo")
    return resumo


def _meses(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Janela em meses do calendário: a API dá 500 em períodos longos e num período com registro
    defeituoso; pedir mês a mês limita o estrago."""
    blocos, de = [], inicio
    while de <= fim:
        proximo = date(de.year + de.month // 12, de.month % 12 + 1, 1)
        ate = min(proximo - timedelta(days=1), fim)
        blocos.append((de, ate))
        de = ate + timedelta(days=1)
    return blocos


def baixar_deputado(
    client: httpx.Client, id_deputado: str, inicio: date, fim: date, falhas: list | None = None
) -> list:
    """Discursos do deputado na janela, mês a mês. Se a API der erro de servidor num período
    (registro defeituoso na fonte), divide o período ao meio até isolar o dia; o dia que continua
    falhando fica de fora e vai para `falhas` (deputado, dia), em vez de abortar a carga inteira."""
    discursos = []
    for de, ate in _meses(inicio, fim):
        discursos += _baixar_periodo(client, id_deputado, de, ate, falhas, TENTATIVAS_MES)
    return discursos


def _baixar_periodo(
    client: httpx.Client,
    id_deputado: str,
    inicio: date,
    fim: date,
    falhas: list | None,
    tentativas: int = 1,
) -> list:
    # Na divisão, uma tentativa só: o 500 de registro defeituoso não passa tentando de novo, e
    # cada nova tentativa custa até 30 s de espera (antes, ~3 min por deputado afetado).
    try:
        return _baixar_paginas(client, id_deputado, inicio, fim, tentativas)
    except httpx.HTTPStatusError as erro:
        if erro.response.status_code < 500:
            raise
    if inicio == fim:
        if falhas is not None:
            falhas.append({"deputado": id_deputado, "dia": inicio.isoformat()})
        print(f"  {FONTE}: deputado {id_deputado}, {inicio}: erro da fonte, dia fica de fora")
        return []
    meio = inicio + (fim - inicio) // 2
    return _baixar_periodo(client, id_deputado, inicio, meio, falhas) + _baixar_periodo(
        client, id_deputado, meio + timedelta(days=1), fim, falhas
    )


def _baixar_paginas(
    client: httpx.Client, id_deputado: str, inicio: date, fim: date, tentativas: int = 1
) -> list:
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
            tentativas=tentativas,
        )
        discursos += [_enxuto(d) for d in resposta.get("dados", [])]
        if not any(link.get("rel") == "next" for link in resposta.get("links", [])):
            return discursos
        pagina += 1
        time.sleep(PAUSA)


def baixar(
    client: httpx.Client, ids: list[str], inicio: date, fim: date, completa: bool
) -> dict[str, Any]:
    deputados, falhas = {}, []
    for id_deputado in ids:
        discursos = baixar_deputado(client, id_deputado, inicio, fim, falhas)
        if discursos:
            deputados[id_deputado] = discursos
        time.sleep(PAUSA)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "completa": completa,
        "deputados": deputados,
        # Dias que a API não conseguiu servir (erro 5xx persistente), por deputado.
        "falhas": falhas,
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
