"""Situação dos processos citados nos eventos (cassações, sanções), lida na API pública do
DataJud (CNJ) pelo número único: classe, órgão julgador, ajuizamento e último andamento.

O DataJud não busca por nome e não cobre o STF: serve para atualizar processos que outra
fonte oficial já ligou a uma pessoa. A chave é pública e trocada de tempos em tempos pelo
CNJ; é lida da página oficial a cada carga (ou de DATAJUD_CHAVE, se definida).

Processo com nível de sigilo acima de zero fica só com o número: nada do conteúdo é
guardado nem publicado. Rode depois das cargas que geram eventos com processo.
"""

import argparse
import html
import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Evento, FonteIngestao, Processo
from ingestion import comum

FONTE = "cnj_datajud"
URL_API = "https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search"
URL_CHAVE = "https://datajud-wiki.cnj.jus.br/api-publica/acesso/"
CNJ = re.compile(r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$")
# Código do tribunal (TR) na Justiça Estadual e Eleitoral: a ordem das UFs da Resolução
# CNJ 65/2008.
UFS = ["ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa",
       "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "se", "sp", "to"]  # fmt: skip
LOTE = 50
PAUSA = 0.5
TENTATIVAS = 4


def alias(numero: str) -> str | None:
    """Índice do DataJud do tribunal do processo, pelo segmento (J) e tribunal (TR)."""
    achado = CNJ.match(numero or "")
    if not achado:
        return None
    j, tr = achado.group(4), int(achado.group(5))
    if j == "3":
        return "stj"
    if j == "4" and 1 <= tr <= 6:
        return f"trf{tr}"
    if j == "6":
        if tr == 0:
            return "tse"
        uf = UFS[tr - 1] if 1 <= tr <= len(UFS) else None
        return None if uf is None else ("tre-dft" if uf == "df" else f"tre-{uf}")
    if j == "8" and 1 <= tr <= len(UFS):
        uf = UFS[tr - 1]
        return "tjdft" if uf == "df" else f"tj{uf}"
    return None  # STF (J=1) não está no DataJud; Trabalho e Militar ainda não usados


def chave(client: httpx.Client) -> str:
    if os.environ.get("DATAJUD_CHAVE"):
        return os.environ["DATAJUD_CHAVE"]
    pagina = html.unescape(re.sub(r"<[^>]+>", " ", client.get(URL_CHAVE).text))
    achado = re.search(r"APIKey atual.{0,40}?APIKey\s+([A-Za-z0-9+/=_-]{30,})", pagina, re.S)
    if not achado:
        raise RuntimeError("Chave pública do DataJud não encontrada na página do CNJ.")
    return achado.group(1)


def _data(valor: str | None) -> date | None:
    """'20240810144421' ou '2024-09-07T14:18:21.000Z' -> date."""
    digitos = re.sub(r"\D", "", valor or "")[:8]
    try:
        return datetime.strptime(digitos, "%Y%m%d").date()
    except ValueError:
        return None


def normalizar(numero: str, hits: list[dict], hoje: date) -> dict[str, Any]:
    """Um registro por processo. Se o processo aparece em mais de um grau, fica o que foi
    atualizado por último."""
    if not hits:
        return {"numero": numero, "encontrado": False, "consultado_em": hoje}
    fonte = max(hits, key=lambda h: h["_source"].get("dataHoraUltimaAtualizacao") or "")["_source"]
    base = {"numero": numero, "tribunal": fonte.get("tribunal"), "encontrado": True,
            "consultado_em": hoje}  # fmt: skip
    if (fonte.get("nivelSigilo") or 0) > 0:
        return {**base, "sigiloso": True}
    movimentos = sorted(fonte.get("movimentos") or [], key=lambda m: m.get("dataHora") or "")
    ultimo = movimentos[-1] if movimentos else {}
    return {
        **base,
        "sigiloso": False,
        "classe": ((fonte.get("classe") or {}).get("nome") or "")[:150] or None,
        "orgao_julgador": ((fonte.get("orgaoJulgador") or {}).get("nome") or "")[:200] or None,
        "data_ajuizamento": _data(fonte.get("dataAjuizamento")),
        "ultimo_andamento": (ultimo.get("nome") or "")[:200] or None,
        "data_ultimo_andamento": _data(ultimo.get("dataHora")),
    }


def numeros_citados(session: Session) -> list[str]:
    return sorted(
        n
        for n in session.scalars(
            select(Evento.numero_processo).where(Evento.numero_processo.is_not(None)).distinct()
        )
        if alias(n)
    )


def _post(client: httpx.Client, url: str, corpo: dict, cabecalhos: dict) -> dict:
    """POST com novas tentativas: os índices do DataJud dão 504 de vez em quando."""
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = client.post(url, json=corpo, headers=cabecalhos)
            if resposta.status_code < 500 and resposta.status_code != 429:
                return resposta.raise_for_status().json()
        except httpx.TransportError:
            if tentativa == TENTATIVAS:
                raise
        time.sleep(5 * tentativa)
    return resposta.raise_for_status().json()


def consultar(client: httpx.Client, numeros: list[str]) -> tuple[dict[str, list[dict]], list[str]]:
    """Hits do DataJud por número (sem pontuação), agrupando por tribunal, e os números que
    não puderam ser consultados (tribunal fora do ar): ficam para a próxima carga."""
    cabecalhos = {"Authorization": f"APIKey {chave(client)}", "Content-Type": "application/json"}
    por_alias: dict[str, list[str]] = {}
    for n in numeros:
        por_alias.setdefault(alias(n), []).append(n)
    resultado: dict[str, list[dict]] = {}
    falharam: list[str] = []
    for indice, lista in por_alias.items():
        for inicio in range(0, len(lista), LOTE):
            lote = lista[inicio : inicio + LOTE]
            time.sleep(PAUSA)
            corpo = {
                "size": LOTE * 4,
                "query": {"terms": {"numeroProcesso": [re.sub(r"\D", "", n) for n in lote]}},
            }
            try:
                dados = _post(client, URL_API.format(alias=indice), corpo, cabecalhos)
            except httpx.HTTPError as erro:
                print(
                    f"  {indice}: {erro.__class__.__name__}; "
                    f"{len(lote)} processos ficam para depois"
                )
                falharam += lote
                continue
            for hit in dados["hits"]["hits"]:
                resultado.setdefault(hit["_source"]["numeroProcesso"], []).append(hit)
    return resultado, falharam


def executar(de_raw: Path | None = None) -> int:
    hoje = date.today()

    def baixar(client: httpx.Client) -> bytes:
        from app.db import SessionLocal

        with SessionLocal() as session:
            numeros = numeros_citados(session)
        hits, falharam = consultar(client, numeros)
        dados = {"numeros": numeros, "hits": hits, "falharam": falharam}
        return json.dumps(dados, ensure_ascii=False).encode()

    def carregar(session: Session, bruto: bytes, ingestao: FonteIngestao) -> int:
        dados = json.loads(bruto)
        falharam = set(dados.get("falharam", []))
        linhas = [
            normalizar(n, dados["hits"].get(re.sub(r"\D", "", n), []), hoje)
            for n in dados["numeros"]
            if n not in falharam
        ]
        for linha in linhas:
            stmt = insert(Processo).values(**linha)
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["numero"],
                    set_={c: stmt.excluded[c] for c in linha if c != "numero"},
                )
            )
        encontrados = sum(1 for linha in linhas if linha["encontrado"])
        print(
            f"  {len(linhas)} processos consultados; {encontrados} encontrados no DataJud; "
            f"{len(falharam)} para a próxima carga"
        )
        return encontrados

    return comum.executar_ingestao(
        FONTE, URL_API.format(alias="..."), baixar, carregar, de_raw=de_raw,
        extensao_raw=".json.gz",
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} processos")
