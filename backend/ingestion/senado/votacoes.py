"""Votações nominais do Plenário do Senado (API de votações).

Cada votação lista todos os senadores, inclusive os ausentes, com um código de
presença (por exemplo LS = licença saúde, MIS = missão, NCom = não compareceu).
"""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion import votacoes_comum as vc

FONTE = "senado_votacoes"
CASA = "senado"
URL = "https://legis.senado.leg.br/dadosabertos/votacao"


def baixar(client: httpx.Client, ano: int) -> list[dict[str, Any]]:
    return comum.get_json(
        client, URL, params={"dataInicio": f"{ano}-01-01", "dataFim": f"{ano}-12-31"}
    )


def normalizar(payload: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    votacoes, votos = [], []
    for v in payload:
        colegiado = (v.get("informeLegislativo") or {}).get("siglaColegiado", "PLEN")
        if colegiado != "PLEN" or not v.get("votos"):
            continue
        id_externo = str(v["codigoSessaoVotacao"])
        votacoes.append(
            {
                "id_externo": id_externo,
                "data": date.fromisoformat(v["dataSessao"][:10]),
                "descricao": " ".join((v.get("descricaoVotacao") or "").split()),
                "proposicao": v.get("identificacao"),
                "secreta": v.get("votacaoSecreta") == "S",
            }
        )
        votos.extend(
            {
                "id_externo_votacao": id_externo,
                "codigo_senador": str(x["codigoParlamentar"]),
                "voto": x.get("siglaVotoParlamentar") or "",
            }
            for x in v["votos"]
        )
    return votacoes, votos


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
        votacoes, votos = normalizar(payload)
        senadores = comum.mapa_parlamentares(session, CASA)
        votos = [
            {**v, "parlamentar_id": senadores[v["codigo_senador"]]}
            for v in votos
            if v["codigo_senador"] in senadores
        ]
        return vc.recarregar_votacoes(session, CASA, ano, votacoes, votos, ingestao)

    return comum.executar_ingestao(
        FONTE, URL, lambda client: baixar(client, ano), carregar, de_raw=de_raw,
        prefixo_raw=f"{ano}_",
    )  # fmt: skip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=comum.anos_padrao())
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} votos")
