"""Peças compartilhadas da ingestão: HTTP, arquivo bruto, registro e cargas.

Fluxo de cada fonte: baixar() grava o bruto em data/raw/<fonte>/ e carregar()
transforma o bruto e grava no banco. As duas etapas são separadas para poder
reprocessar o bruto sem rede (--de-raw).
"""

import argparse
import gzip
import json
import re
import shutil
import tempfile
import time
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import Despesa, FonteIngestao, Parlamentar

RAW_DIR = BACKEND_DIR / "data" / "raw"
USER_AGENT = "Panoptico/0.1 (+https://panoptico.social.br)"
# Brutos maiores que isto não são lidos para a memória: carregar_raw devolve o caminho.
LIMITE_EM_MEMORIA = 200_000_000

Baixar = Callable[[httpx.Client], Any]
Normalizar = Callable[[Any], list[dict[str, Any]]]
Carregar = Callable[[Session, Any, FonteIngestao], int]


def criar_cliente() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(30.0, read=120.0),
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def _espera(resposta: httpx.Response | None, tentativa: int) -> float:
    """Quanto esperar antes de tentar de novo: o Retry-After da fonte, se houver."""
    if resposta is not None:
        retry_after = resposta.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(int(retry_after), 60)
    return float(2**tentativa)


def _get(client: httpx.Client, url: str, params: dict | None, tentativas: int) -> httpx.Response:
    """GET com novas tentativas para falhas de rede, erros 5xx e limite de taxa (429)."""
    resposta = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.get(url, params=params)
            if resposta.status_code < 500 and resposta.status_code != 429:
                return resposta.raise_for_status()
        except httpx.TransportError:
            if tentativa == tentativas:
                raise
        if tentativa < tentativas:
            time.sleep(_espera(resposta, tentativa))
    return resposta.raise_for_status()


def get_json(client: httpx.Client, url: str, params: dict | None = None, tentativas: int = 3):
    return _get(client, url, params, tentativas).json()


def get_bytes(client: httpx.Client, url: str, tentativas: int = 3) -> bytes:
    return _get(client, url, None, tentativas).content


def baixar_para_arquivo(client: httpx.Client, url: str) -> Path:
    """Baixa em fluxo para um arquivo temporário, sem passar o conteúdo pela memória (para
    arquivos de centenas de MB, como as contas de campanha do TSE)."""
    with client.stream("GET", url, timeout=600) as resposta:
        resposta.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as destino:
            for bloco in resposta.iter_bytes(1 << 20):
                destino.write(bloco)
    return Path(destino.name)


def salvar_raw(fonte: str, payload: Any, prefixo: str = "", extensao: str = ".zip") -> Path:
    """Grava o bruto. Bytes são gravados como vieram (comprimidos com gzip se a extensão
    terminar em .gz); qualquer outro payload vira JSON."""
    destino = RAW_DIR / fonte
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{prefixo}{datetime.now():%Y-%m-%d_%H%M%S}"
    if isinstance(payload, Path):  # já baixado em disco (baixar_para_arquivo)
        arquivo = destino / f"{nome}{extensao}"
        shutil.move(payload, arquivo)
        return arquivo
    if isinstance(payload, bytes):
        arquivo = destino / f"{nome}{extensao}"
        arquivo.write_bytes(gzip.compress(payload) if extensao.endswith(".gz") else payload)
    else:
        arquivo = destino / f"{nome}.json"
        arquivo.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return arquivo


def carregar_raw(arquivo: Path) -> Any:
    arquivo = Path(arquivo)
    if arquivo.suffix == ".json":
        return json.loads(arquivo.read_text(encoding="utf-8"))
    if arquivo.suffix == ".gz":
        return gzip.decompress(arquivo.read_bytes())
    if arquivo.stat().st_size > LIMITE_EM_MEMORIA:
        return arquivo
    return arquivo.read_bytes()


def mapa_parlamentares(session: Session, casa: str) -> dict[str, int]:
    """id_externo -> id interno, para ligar dados de outras fontes ao parlamentar."""
    linhas = session.execute(
        select(Parlamentar.id_externo, Parlamentar.id).where(Parlamentar.casa == casa)
    )
    return {id_externo: id_ for id_externo, id_ in linhas}


def vincular_parlamentares(
    session: Session, casa: str, registros: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Troca o id externo pelo id interno e descarta quem não está na base."""
    mapa = mapa_parlamentares(session, casa)
    linhas = []
    for r in registros:
        parlamentar_id = mapa.get(r["id_externo_parlamentar"])
        if parlamentar_id is not None:
            linha = {k: v for k, v in r.items() if k != "id_externo_parlamentar"}
            linhas.append({**linha, "parlamentar_id": parlamentar_id})
    return linhas


def upsert_parlamentares(
    session: Session, casa: str, registros: list[dict[str, Any]], ingestao: FonteIngestao
) -> int:
    """Faz upsert da lista e marca os demais parlamentares da casa como fora de exercício."""
    if not registros:
        raise ValueError(f"Nenhum registro para {casa}; abortando para não zerar a casa.")

    agora = datetime.now(UTC)
    linhas = [
        {
            **r,
            "casa": casa,
            "em_exercicio": True,
            "atualizado_em": agora,
            "ingestao_id": ingestao.id,
        }
        for r in registros
    ]
    stmt = insert(Parlamentar).values(linhas)
    colunas_atualizaveis = {
        c: stmt.excluded[c] for c in linhas[0] if c not in ("casa", "id_externo")
    }
    session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_parlamentar_casa_id_externo", set_=colunas_atualizaveis
        )
    )

    ids = [r["id_externo"] for r in registros]
    session.execute(
        update(Parlamentar)
        .where(Parlamentar.casa == casa, Parlamentar.id_externo.not_in(ids))
        .values(em_exercicio=False, atualizado_em=agora)
    )
    return len(linhas)


def chave_nome(nome: str | None) -> str:
    """Chave para comparar nomes: 'Dr. Flávio' -> 'DR FLAVIO'."""
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Z ]", " ", sem_acento.upper()).split())


PARTICULAS = {"da", "das", "de", "do", "dos", "e"}


def nome_proprio(nome: str | None) -> str | None:
    """'MARIA DA SILVA' -> 'Maria da Silva'. Nomes já em caixa mista ficam como estão."""
    if not nome or not nome.isupper():
        return nome
    palavras = nome.lower().split()
    return " ".join(
        p if i > 0 and p in PARTICULAS else p[:1].upper() + p[1:] for i, p in enumerate(palavras)
    )


def limpar_categoria(texto: str | None) -> str:
    """Padroniza o nome da categoria de gasto (a Câmara publica tudo em maiúsculas)."""
    t = re.sub(r"\s*,\s*", ", ", " ".join((texto or "").split())).rstrip(".").strip()
    if not t:
        return "Não informado"
    return t[0].upper() + t[1:].lower() if t.isupper() else t


def recarregar_despesas(
    session: Session, casa: str, ano: int, linhas: list[dict[str, Any]], ingestao: FonteIngestao
) -> int:
    """Substitui as despesas de uma casa num ano. Os arquivos oficiais são anuais e mudam
    retroativamente (glosas, restituições), então recarregar o ano inteiro é o mais seguro."""
    if not linhas:
        raise ValueError(f"Nenhuma despesa de {casa} em {ano}; abortando para não zerar o ano.")
    session.execute(delete(Despesa).where(Despesa.casa == casa, Despesa.ano == ano))
    base = {"casa": casa, "ano": ano, "ingestao_id": ingestao.id}
    for inicio in range(0, len(linhas), 5000):
        lote = [{**base, **linha} for linha in linhas[inicio : inicio + 5000]]
        session.execute(sa_insert(Despesa), lote)
    return len(linhas)


def anos_padrao() -> list[int]:
    ano = datetime.now().year
    return [ano - 1, ano]


def executar_ingestao(
    fonte: str,
    url: str,
    baixar: Baixar,
    carregar: Carregar,
    de_raw: Path | None = None,
    prefixo_raw: str = "",
    extensao_raw: str = ".zip",
) -> int:
    """Baixa (ou lê o bruto), grava o bruto e roda a carga numa transação registrada."""
    if de_raw is None:
        with criar_cliente() as client:
            payload = baixar(client)
        arquivo = salvar_raw(fonte, payload, prefixo_raw, extensao_raw)
        if isinstance(payload, Path):  # o arquivo foi movido para o raw
            payload = arquivo
    else:
        arquivo = Path(de_raw)
        payload = carregar_raw(arquivo)

    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=fonte, url=url, arquivo_raw=str(arquivo))
        session.add(ingestao)
        session.flush()
        try:
            total = carregar(session, payload, ingestao)
            ingestao.registros = total
            ingestao.status = "ok"
            ingestao.concluido_em = datetime.now(UTC)
            session.commit()
        except Exception:
            session.rollback()
            session.add(
                FonteIngestao(
                    fonte=fonte,
                    url=url,
                    arquivo_raw=str(arquivo),
                    status="erro",
                    concluido_em=datetime.now(UTC),
                )
            )
            session.commit()
            raise
    return total


def executar(
    fonte: str,
    casa: str,
    url: str,
    baixar: Baixar,
    normalizar: Normalizar,
    de_raw: Path | None = None,
) -> int:
    """Ingestão da lista de parlamentares de uma casa."""

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        return upsert_parlamentares(session, casa, normalizar(payload), ingestao)

    return executar_ingestao(fonte, url, baixar, carregar, de_raw=de_raw)


def main(fonte: str, casa: str, url: str, baixar: Baixar, normalizar: Normalizar) -> None:
    parser = argparse.ArgumentParser(description=f"Ingestão: {fonte}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    total = executar(fonte, casa, url, baixar, normalizar, de_raw=args.de_raw)
    print(f"{fonte}: {total} registros")
