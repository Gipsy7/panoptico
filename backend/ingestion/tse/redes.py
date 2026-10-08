"""Redes sociais e sites informados pelos candidatos ao TSE (rede_social_candidato).

Rode depois de ingestion.tse.candidaturas do mesmo ano: liga pelo SQ_CANDIDATO.
"""

import argparse
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Candidatura, FonteIngestao, RedeSocial
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_redes"
URL = f"{comum_tse.BASE}/consulta_cand/rede_social_candidato_{{ano}}.zip"


def normalizar(linhas: Any, candidaturas: dict[str, int]) -> list[dict[str, Any]]:
    """Só endereços web, sem repetir o mesmo endereço na mesma candidatura."""
    vistos: set[tuple[int, str]] = set()
    redes = []
    for linha in linhas:
        id_ = candidaturas.get(linha["SQ_CANDIDATO"].strip())
        url = (linha.get("DS_URL") or "").strip()
        if id_ is None or not url.lower().startswith(("http://", "https://")):
            continue
        if (id_, url.lower()) in vistos:
            continue
        vistos.add((id_, url.lower()))
        redes.append({"candidatura_id": id_, "url": url})
    return redes


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        candidaturas = dict(
            session.execute(
                select(Candidatura.sq_candidato, Candidatura.id).where(
                    Candidatura.ano_eleicao == ano
                )
            ).all()
        )
        if not candidaturas:
            return 0
        redes = normalizar(comum_tse.linhas(payload, "rede_social_candidato_"), candidaturas)
        session.execute(
            delete(RedeSocial).where(
                RedeSocial.candidatura_id.in_(
                    select(Candidatura.id).where(Candidatura.ano_eleicao == ano)
                )
            )
        )
        for inicio in range(0, len(redes), 5000):
            session.execute(insert(RedeSocial), redes[inicio : inicio + 5000])
        return len(redes)

    return comum.executar_ingestao(
        FONTE, URL.format(ano=ano), baixar, carregar, de_raw=de_raw, prefixo_raw=f"{ano}_"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2018, 2022, 2024])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} endereços")
