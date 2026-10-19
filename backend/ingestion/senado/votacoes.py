"""Votações nominais do Plenário do Senado (API de votações).

Cada votação lista todos os senadores, inclusive os ausentes, com um código de
presença (por exemplo LS = licença saúde, MIS = missão, NCom = não compareceu).

As orientações das lideranças (entre elas a do Governo) vêm de outro endpoint, um por
dia de sessão, e são ligadas à votação pelo número sequencial (`sequencialVotacao`).
Só existem em parte das votações abertas; nas secretas não há orientação.
O bruto guarda as duas respostas juntas; brutos antigos (só a lista) seguem válidos.

Nas orientações, o partido vem pelo nome de uso ("Progressistas", "Podemos"), não pela sigla
dos votos ("PP", "PODE"). A mesma resposta traz o voto de cada senador com esse nome de
partido; casando pelo nome do senador com a lista de votos, achamos a sigla. Rótulo que não
casa com nenhum partido (ex.: "B.Feminina") fica como a fonte publica, com tipo "outra".
"""

import argparse
from collections import Counter, defaultdict
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
RESULTADOS = {"A": "aprovada", "R": "rejeitada"}


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
    orientacoes = {}
    for data in datas:
        try:
            orientacoes[data] = comum.get_json(
                client, URL_ORIENTACOES.format(data=data.replace("-", ""))
            )
        except httpx.HTTPError as erro:
            # As orientações são um complemento: uma data fora do ar não derruba o ano.
            print(f"[aviso] orientações de {data} puladas: {erro!r}", flush=True)
    return {"votacoes": votacoes, "orientacoes": orientacoes}


def _siglas_dos_rotulos(
    payload: dict[str, Any], siglas_por_nome: dict[str, dict[str, str]],
    por_sequencial: dict[tuple[str, int], str],
) -> dict[str, str]:  # fmt: skip
    """Rótulo de partido das orientações ("Progressistas") -> sigla dos votos ("PP"), pela
    sigla mais comum entre os senadores de mesmo nome nas mesmas votações."""
    contagem: dict[str, Counter] = defaultdict(Counter)
    for data, resposta in payload.get("orientacoes", {}).items():
        for v in (resposta or {}).get("votacoes", []):
            siglas = siglas_por_nome.get(por_sequencial.get((data, v.get("sequencialVotacao"))))
            if not siglas:
                continue
            for x in v.get("votosParlamentar") or []:
                sigla = siglas.get(x.get("nomeParlamentar") or "")
                if sigla and x.get("partido"):
                    contagem[x["partido"]][sigla] += 1
    return {rotulo: c.most_common(1)[0][0] for rotulo, c in contagem.items()}


def _orientacoes(
    payload: dict[str, Any], por_sequencial: dict[tuple[str, int], str],
    siglas_por_nome: dict[str, dict[str, str]] | None = None,
) -> list[dict]:  # fmt: skip
    """Orientações de lideranças (Governo...) e de partidos; outras bancadas com tipo
    "outra". Liderança sem orientação reconhecida fica de fora, como antes."""
    sigla_do_rotulo = _siglas_dos_rotulos(payload, siglas_por_nome or {}, por_sequencial)
    resultado = []
    for data, resposta in payload.get("orientacoes", {}).items():
        for v in (resposta or {}).get("votacoes", []):
            id_externo = por_sequencial.get((data, v.get("sequencialVotacao")))
            if id_externo is None:
                continue
            for o in v.get("orientacoesLideranca") or []:
                orientacao = ORIENTACOES.get((o.get("voto") or "").strip().upper())
                rotulo = (o.get("partido") or "").strip()
                if not orientacao or not rotulo:
                    continue
                registro = {"id_externo_votacao": id_externo, "orientacao": orientacao}
                if rotulo in vc.BANCADAS:
                    resultado.append(registro | {"bancada": rotulo, "tipo": "lideranca"})
                elif rotulo in sigla_do_rotulo:
                    resultado.append(
                        registro | {"bancada": sigla_do_rotulo[rotulo], "tipo": "partido"}
                    )
                else:
                    resultado.append(registro | {"bancada": rotulo, "tipo": "outra"})
    return resultado


def normalizar(payload: dict[str, Any] | list) -> tuple[list[dict], list[dict], list[dict]]:
    """Devolve (votações, votos, orientações)."""
    if isinstance(payload, list):  # bruto antigo, sem orientações
        payload = {"votacoes": payload, "orientacoes": {}}
    votacoes, votos, por_sequencial = [], [], {}
    siglas_por_nome: dict[str, dict[str, str]] = {}
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
                "resultado": RESULTADOS.get(v.get("resultadoVotacao") or ""),
                "placar_sim": v.get("totalVotosSim"),
                "placar_nao": v.get("totalVotosNao"),
                "placar_abstencao": v.get("totalVotosAbstencao"),
            }
        )
        siglas_por_nome[id_externo] = {
            x["nomeParlamentar"]: x["siglaPartidoParlamentar"]
            for x in v["votos"]
            if x.get("nomeParlamentar") and x.get("siglaPartidoParlamentar")
        }
        votos.extend(
            {
                "id_externo_votacao": id_externo,
                "codigo_senador": str(x["codigoParlamentar"]),
                "voto": x.get("siglaVotoParlamentar") or "",
                "partido": x.get("siglaPartidoParlamentar") or None,
            }
            for x in v["votos"]
        )
    return votacoes, votos, _orientacoes(payload, por_sequencial, siglas_por_nome)


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
