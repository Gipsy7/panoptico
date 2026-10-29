"""Medidas provisórias e vetos do Presidente da República no mandato atual (desde 2023).

API de processos do Senado (a mesma de `senado/proposicoes.py`; aberta, sem token):
`/processo?sigla=MPV&ano=AAAA` e `/processo?sigla=VET&ano=AAAA`, uma lista JSON por ano. O
Congresso Nacional numera MPV e VET por ano civil, e todos os de 2023 em diante são do
presidente do mandato 2023-2026 (a primeira MPV de 2023 é a 1.154, de 1º/1; o primeiro veto, de
11/1). Cada item traz a identificação ("MPV 1287/2025"), a ementa, a data, `situacaoAtual` (só
MPV, texto do Congresso), `siglaTipoDeliberacao` (o que o Congresso decidiu: PERDA_EFICACIA,
APROVADO_PLV, MANTIDA_MATE, REJEITADO_PLENARIO, MANTIDO_PARCIALMENTE, PREJUDICADO; ausente
enquanto não decidiu) e `tramitando`.

Veto total ou parcial não é campo da lista: vem do início da ementa ("Veto Parcial aposto ao
Projeto de Lei...", "Veto Total...", "Veto Integral..."); conferido contra o serviço antigo
`/materia/vetos/{ano}` (campo `Total`) em 2023-2026, com os mesmos totais. O bruto é um
dicionário {"mpv": [...], "veto": [...]}. Recarga integral (uma transação): ~450 linhas.
"""

import argparse
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import AtoPresidencial, FonteIngestao
from ingestion import comum

FONTE = "congresso_atos_presidente"
URL = "https://legis.senado.leg.br/dadosabertos/processo"
URL_MPV = "https://www.congressonacional.leg.br/materias/medidas-provisorias/-/mpv/{codigo}"
URL_VETO = "https://www.congressonacional.leg.br/materias/vetos/-/veto/detalhe/{codigo}"
PRIMEIRA_ELEICAO = 2022  # a eleição presidencial mais antiga que a carga cobre
SIGLAS = {"mpv": "MPV", "veto": "VET"}
PAUSA = 0.3


def posse(ano_eleicao: int) -> date:
    """Posse do Presidente eleito no ano: 1º de janeiro até 2023; 5 de janeiro a partir de 2027
    (EC 111/2021, que também estende até lá o mandato eleito em 2022)."""
    return date(ano_eleicao + 1, 1, 5 if ano_eleicao + 1 >= 2027 else 1)


def mandato_em_curso(hoje: date | None = None) -> dict:
    """Mandato presidencial em curso: a eleição (de 4 em 4 anos desde 2022) mais recente cuja
    posse já ocorreu. `fim` é o dia anterior à posse seguinte."""
    hoje = hoje or date.today()
    ano = PRIMEIRA_ELEICAO
    while posse(ano + 4) <= hoje:
        ano += 4
    proxima = posse(ano + 4)
    return {"ano_eleicao": ano, "inicio": posse(ano), "fim": proxima - timedelta(days=1)}


def _data(valor: str | None) -> date | None:
    try:
        return date.fromisoformat((valor or "")[:10])
    except ValueError:
        return None


def veto_total(ementa: str) -> bool | None:
    inicio = ementa.strip().lower()
    if inicio.startswith(("veto total", "veto integral")):
        return True
    if inicio.startswith("veto parcial"):
        return False
    return None


def normalizar(
    payload: dict[str, list[dict[str, Any]]], inicio: date | None = None
) -> list[dict[str, Any]]:
    """Itens do bruto -> linhas de `ato_presidencial` (só do mandato em curso; sem repetidos)."""
    inicio = inicio or mandato_em_curso()["inicio"]
    vistos: set[tuple[str, str]] = set()
    linhas: list[dict[str, Any]] = []
    for tipo, sigla in SIGLAS.items():
        for p in payload.get(tipo, []):
            ident = (p.get("identificacao") or "").strip()
            sigla_e_resto = ident.split(" ", 1)
            if sigla_e_resto[0] != sigla or "/" not in ident:
                continue
            data = _data(p.get("dataApresentacao"))
            codigo = str(p.get("codigoMateria") or "")
            if data is None or data < inicio or not codigo or (tipo, codigo) in vistos:
                continue
            vistos.add((tipo, codigo))
            numero, ano = sigla_e_resto[1].split("/")
            ementa = (p.get("ementa") or "").strip()
            linhas.append(
                {
                    "tipo": tipo,
                    "id_externo": codigo,
                    "identificacao": ident,
                    "numero": int(numero.replace(".", "")),
                    "ano": int(ano),
                    "ementa": ementa,
                    "apelido": (p.get("apelido") or "").strip() or None,
                    "data": data,
                    "data_decisao": _data(p.get("dataDeliberacao")),
                    "situacao": (p.get("situacaoAtual") or "").strip() or None,
                    "decisao": p.get("siglaTipoDeliberacao") or None,
                    "tramitando": p.get("tramitando") == "Sim",
                    "veto_total": veto_total(ementa) if tipo == "veto" else None,
                    "norma_gerada": (p.get("normaGerada") or "").strip()[:200] or None,
                    "url": (URL_MPV if tipo == "mpv" else URL_VETO).format(codigo=codigo),
                }
            )
    return linhas


def baixar(client: httpx.Client, ate: int | None = None) -> dict[str, list]:
    ate = ate or datetime.now().year
    payload: dict[str, list] = {}
    for tipo, sigla in SIGLAS.items():
        payload[tipo] = []
        for ano in range(mandato_em_curso()["inicio"].year, ate + 1):
            lista = comum.get_json(client, URL, params={"sigla": sigla, "ano": ano})
            payload[tipo].extend(lista if isinstance(lista, list) else [])
            time.sleep(PAUSA)
    return payload


def gravar(session: Session, linhas: list[dict[str, Any]], ingestao_id: int) -> None:
    session.execute(delete(AtoPresidencial))
    session.execute(insert(AtoPresidencial), [{**r, "ingestao_id": ingestao_id} for r in linhas])


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    for tipo in SIGLAS:
        if not any(r["tipo"] == tipo for r in linhas):
            raise RuntimeError(f"Congresso sem {tipo} no período: nada alterado.")
    total = sum(len(payload.get(t, [])) for t in SIGLAS)
    comum.conferir_carga(
        ingestao, linhas, total_fonte=total, unica=["tipo", "id_externo"],
        nao_nulos=["ementa", "data"],
    )  # fmt: skip
    gravar(session, linhas, ingestao.id)
    mpv = sum(1 for r in linhas if r["tipo"] == "mpv")
    print(f"  {mpv} medidas provisórias e {len(linhas) - mpv} vetos desde 2023")
    return len(linhas)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um JSON bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.de_raw)} atos")
