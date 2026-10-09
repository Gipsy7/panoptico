"""Bens declarados pelos candidatos ao TSE (bem_candidato), só das candidaturas guardadas.

Rode depois de ingestion.tse.candidaturas do mesmo ano: os bens se ligam pela candidatura
(SQ_CANDIDATO). O valor é o declarado pelo próprio candidato, sem correção.
"""

import argparse
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import BemDeclarado, Candidatura, FonteIngestao
from ingestion import comum
from ingestion.tse import comum_tse

FONTE = "tse_bens"
URL = f"{comum_tse.BASE}/bem_candidato/bem_candidato_{{ano}}.zip"


def normalizar(linhas: Any, candidaturas: dict[str, int]) -> list[dict[str, Any]]:
    """Só os bens das candidaturas de interesse (SQ -> id da candidatura)."""
    return [
        {
            "candidatura_id": candidaturas[sq],
            "ordem": int(linha.get("NR_ORDEM_BEM_CANDIDATO") or 0),
            "tipo": comum_tse.texto(linha.get("DS_TIPO_BEM_CANDIDATO")) or "Não informado",
            "descricao": (linha.get("DS_BEM_CANDIDATO") or "").strip(),
            "valor": comum_tse.valor(linha.get("VR_BEM_CANDIDATO")),
        }
        for linha in linhas
        if (sq := linha["SQ_CANDIDATO"].strip()) in candidaturas
    ]


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
        bens = normalizar(comum_tse.linhas(payload, "bem_candidato_"), candidaturas)
        session.execute(
            delete(BemDeclarado).where(
                BemDeclarado.candidatura_id.in_(
                    select(Candidatura.id).where(Candidatura.ano_eleicao == ano)
                )
            )
        )
        for inicio in range(0, len(bens), 5000):
            session.execute(insert(BemDeclarado), bens[inicio : inicio + 5000])
        return len(bens)

    return comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(
            sonda=URL.format(ano=ano), contexto=comum.contexto_candidaturas(ano)
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2018, 2022])
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} bens")
