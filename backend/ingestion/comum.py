"""Peças compartilhadas da ingestão: HTTP, arquivo bruto, registro e upsert.

Fluxo de cada fonte: baixar() grava o JSON bruto em data/raw/<fonte>/ e
normalizar() transforma o bruto em registros de parlamentar. As duas etapas são
separadas para poder reprocessar o bruto sem rede (--de-raw).
"""

import argparse
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import FonteIngestao, Parlamentar

RAW_DIR = BACKEND_DIR / "data" / "raw"
USER_AGENT = "Panoptico/0.1 (+https://panoptico.social.br)"

Baixar = Callable[[httpx.Client], Any]
Normalizar = Callable[[Any], list[dict[str, Any]]]


def criar_cliente() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def get_json(client: httpx.Client, url: str, params: dict | None = None, tentativas: int = 3):
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.get(url, params=params)
            if resposta.status_code < 500:
                resposta.raise_for_status()
                return resposta.json()
        except httpx.TransportError:
            if tentativa == tentativas:
                raise
        if tentativa < tentativas:
            time.sleep(2**tentativa)
    resposta.raise_for_status()


def salvar_raw(fonte: str, payload: Any) -> Path:
    destino = RAW_DIR / fonte
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / f"{datetime.now():%Y-%m-%d_%H%M%S}.json"
    arquivo.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return arquivo


def carregar_raw(arquivo: Path) -> Any:
    return json.loads(Path(arquivo).read_text(encoding="utf-8"))


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


def executar(
    fonte: str,
    casa: str,
    url: str,
    baixar: Baixar,
    normalizar: Normalizar,
    de_raw: Path | None = None,
) -> int:
    if de_raw is None:
        with criar_cliente() as client:
            payload = baixar(client)
        arquivo = salvar_raw(fonte, payload)
    else:
        arquivo = Path(de_raw)
        payload = carregar_raw(arquivo)

    registros = normalizar(payload)

    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=fonte, url=url, arquivo_raw=str(arquivo))
        session.add(ingestao)
        session.flush()
        try:
            total = upsert_parlamentares(session, casa, registros, ingestao)
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


def main(fonte: str, casa: str, url: str, baixar: Baixar, normalizar: Normalizar) -> None:
    parser = argparse.ArgumentParser(description=f"Ingestão: {fonte}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    total = executar(fonte, casa, url, baixar, normalizar, de_raw=args.de_raw)
    print(f"{fonte}: {total} registros")
