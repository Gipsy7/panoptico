"""Votações nominais do Plenário do Senado (API de votações).

Cada votação lista todos os senadores, inclusive os ausentes, com um código de
presença (por exemplo LS = licença saúde, MIS = missão, NCom = não compareceu).

As orientações das lideranças (entre elas a do Governo) vêm de outro endpoint, um por
dia de sessão, e são ligadas à votação pelo número sequencial (`sequencialVotacao`).
Só existem em parte das votações abertas; nas secretas não há orientação.
O bruto guarda as duas respostas juntas; brutos antigos (só a lista) seguem válidos.
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
URL_ORIENTACOES = (
    "https://legis.senado.leg.br/dadosabertos/plenario/votacao/orientacaoBancada/{data}"
)
ORIENTACOES = {
    "SIM": "Sim",
    "NÃO": "Não",
    "NAO": "Não",
    "LIVRE": "Liberado",
    "OBSTRUÇÃO": "Obstrução",
    "ABSTENÇÃO": "Abstenção",
}


def baixar(client: httpx.Client, ano: int) -> dict[str, Any]:
    votacoes = comum.get_json(
        client, URL, params={"dataInicio": f"{ano}-01-01", "dataFim": f"{ano}-12-31"}
    )
    datas = sorted(
        {
            v["dataSessao"][:10]
            for v in votacoes
            if v.get("votacaoSecreta") != "S" and v.get("votos")
        }
    )
    orientacoes = {
        data: comum.get_json(client, URL_ORIENTACOES.format(data=data.replace("-", "")))
        for data in datas
    }
    return {"votacoes": votacoes, "orientacoes": orientacoes}


def _orientacoes(payload: dict[str, Any], por_sequencial: dict[tuple[str, int], str]) -> list[dict]:
    resultado = []
    for data, resposta in payload.get("orientacoes", {}).items():
        for v in (resposta or {}).get("votacoes", []):
            id_externo = por_sequencial.get((data, v.get("sequencialVotacao")))
            if id_externo is None:
                continue
            for o in v.get("orientacoesLideranca") or []:
                orientacao = ORIENTACOES.get((o.get("voto") or "").strip().upper())
                if orientacao and o.get("partido") in vc.BANCADAS:
                    resultado.append(
                        {"id_externo_votacao": id_externo, "bancada": o["partido"],
                         "orientacao": orientacao}
                    )  # fmt: skip
    return resultado


def normalizar(payload: dict[str, Any] | list) -> tuple[list[dict], list[dict], list[dict]]:
    """Devolve (votações, votos, orientações)."""
    if isinstance(payload, list):  # bruto antigo, sem orientações
        payload = {"votacoes": payload, "orientacoes": {}}
    votacoes, votos, por_sequencial = [], [], {}
    for v in payload["votacoes"]:
        colegiado = (v.get("informeLegislativo") or {}).get("siglaColegiado", "PLEN")
        if colegiado != "PLEN" or not v.get("votos"):
            continue
        id_externo = str(v["codigoSessaoVotacao"])
        por_sequencial[(v["dataSessao"][:10], v.get("sequencialVotacao"))] = id_externo
        votacoes.append(
            {
                "id_externo": id_externo,
                "data": date.fromisoformat(v["dataSessao"][:10]),
                "descricao": " ".join((v.get("descricaoVotacao") or "").split()),
                "proposicao": v.get("identificacao"),
                "proposicao_id_externo": str(v["codigoMateria"])
                if v.get("codigoMateria")
                else None,
                "proposicao_ementa": " ".join((v.get("ementa") or "").split()) or None,
                "secreta": v.get("votacaoSecreta") == "S",
            }
        )
        votos.extend(
            {
                "id_externo_votacao": id_externo,
                "codigo_senador": str(x["codigoParlamentar"]),
                "voto": x.get("siglaVotoParlamentar") or "",
                "partido": x.get("siglaPartidoParlamentar") or None,
            }
            for x in v["votos"]
        )
    return votacoes, votos, _orientacoes(payload, por_sequencial)


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, payload: dict | list, ingestao: FonteIngestao) -> int:
        votacoes, votos, orientacoes = normalizar(payload)
        senadores = comum.mapa_parlamentares(session, CASA)
        votos = [
            {**v, "parlamentar_id": senadores[v["codigo_senador"]]}
            for v in votos
            if v["codigo_senador"] in senadores
        ]
        return vc.recarregar_votacoes(
            session, CASA, ano, votacoes, votos, ingestao, orientacoes=orientacoes
        )

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
