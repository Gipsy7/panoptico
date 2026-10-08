"""Votações nominais nas comissões do Senado (dados abertos do Senado).

O Senado publica as votações de comissão por colegiado ou por senador; consultamos por
senador em exercício (um pedido por senador e ano) e juntamos pelo código da votação. Cada
votação traz a lista completa de quem votou nela.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import FonteIngestao, Parlamentar
from ingestion import comum
from ingestion import votacoes_comum as vc

FONTE = "senado_votacoes_comissoes"
CASA = "senado"
URL = "https://legis.senado.leg.br/dadosabertos/votacaoComissao/parlamentar/{codigo}"
VOTOS = {"S": "Sim", "N": "Não", "A": "Abstenção"}


def _lista(valor: Any) -> list:
    """O Senado devolve objeto quando há um item só e lista quando há vários."""
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def normalizar(respostas: list[dict]) -> tuple[list[dict], list[dict]]:
    votacoes: dict[str, dict] = {}
    votos: list[dict] = []
    for resposta in respostas:
        bloco = (resposta.get("VotacoesComissao") or {}).get("Votacoes") or {}
        for v in _lista(bloco.get("Votacao")):
            codigo = str(v["CodigoVotacao"])
            if codigo in votacoes:
                continue
            votacoes[codigo] = {
                "id_externo": codigo,
                "orgao_sigla": v.get("SiglaColegiado") or "?",
                "orgao_nome": v.get("NomeColegiado"),
                "data": date.fromisoformat(v["DataHoraInicioReuniao"][:10]),
                "descricao": " ".join((v.get("DescricaoVotacao") or "").split()),
                "proposicao": v.get("IdentificacaoMateria"),
            }
            votos.extend(
                {
                    "id_externo_votacao": codigo,
                    "codigo_senador": str(x["CodigoParlamentar"]),
                    "voto": VOTOS.get(x.get("QualidadeVoto") or "", x.get("QualidadeVoto") or ""),
                }
                for x in _lista((v.get("Votos") or {}).get("Voto"))
                if x.get("SiglaCasaParlamentar", "SF") == "SF"
            )
    return list(votacoes.values()), votos


def baixar(client: httpx.Client, ano: int) -> list[dict]:
    with SessionLocal() as session:
        codigos = session.scalars(
            select(Parlamentar.id_externo).where(Parlamentar.casa == CASA, Parlamentar.em_exercicio)
        ).all()
    params = {"dataInicio": f"{ano}0101", "dataFim": f"{ano}1231"}

    def buscar(codigo: str) -> dict | None:
        try:
            return comum.get_json(client, URL.format(codigo=codigo), params=params)
        except httpx.HTTPError:
            return None  # um senador sem resposta não derruba a carga; o próximo dia completa

    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(pool.map(buscar, codigos))
    falhas = sum(r is None for r in respostas)
    if falhas > len(respostas) / 2:  # fonte fora do ar: não apagar o que já existe
        raise RuntimeError(f"{falhas} de {len(respostas)} consultas falharam")
    return [r for r in respostas if r is not None]


def executar(ano: int, de_raw: Path | None = None) -> int:
    def carregar(session: Session, payload: list, ingestao: FonteIngestao) -> int:
        votacoes, votos = normalizar(payload)
        senadores = comum.mapa_parlamentares(session, CASA)
        votos = [
            {**v, "parlamentar_id": senadores[v["codigo_senador"]]}
            for v in votos
            if v["codigo_senador"] in senadores
        ]
        return vc.recarregar_comissoes(session, CASA, ano, votacoes, votos, ingestao)

    return comum.executar_ingestao(
        FONTE,
        URL.format(codigo="{codigo}"),
        lambda client: baixar(client, ano),
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=comum.anos_padrao())
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} votos")
