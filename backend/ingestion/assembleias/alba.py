"""Assembleia Legislativa da Bahia (ALBA): deputados no cargo hoje, proposições de autoria e
presença em plenário, pela API pública de dados abertos do Processo Legislativo Eletrônico
(albalegis.nopapercloud.com.br/dados-abertos.aspx).

- `/api/publico/parlamentar/`: os deputados (nome, nome civil, partido, foto, e-mail,
  situação) e, para cada um, a frequência em plenário por ano (presente, falta, falta
  justificada, licença...).
- `/api/publico/proposicao/?ano=AAAA`: todas as proposições do ano, com tipo, ementa, data,
  situação e o autor. Projetos (lei, lei complementar, emenda à Constituição, decreto
  legislativo e resolução) são guardados com a ementa; indicações, moções, requerimentos e
  utilidade pública entram só como contagem.

A lógica é a do PLE, compartilhada com a ALES (`ple.py`); aqui ficam o endereço e as siglas.
A API não publica votos nominais nem verba de gabinete. Uma requisição por vez, com pausa.
"""

import argparse
from datetime import date
from typing import Any

from ingestion.assembleias import ple

FONTE = "alba"
SITE = "https://albalegis.nopapercloud.com.br/"
API = SITE + "api/publico/"
PAUSA = 1.0
POR_PAGINA = ple.POR_PAGINA
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PRS": "Projeto de Resolução",
}
CONTAGEM = {
    "IND": "Indicação",
    "MOC": "Moção",
    "REQ": "Requerimento",
    "UP": "Utilidade Pública",
}

deputados = ple.deputados
frequencia = ple.frequencia


def distribuir(props: list[dict], parlamentares: list[dict]) -> dict[str, dict]:
    return ple.distribuir(props, parlamentares, API, PROJETOS, CONTAGEM)


def baixar_proposicoes(client: Any, ano: int) -> list[dict]:
    return ple.baixar_proposicoes(client, API, ano, PAUSA)


def coletar(hoje: date) -> dict:
    return ple.coletar(hoje, site=SITE, api=API, pausa=PAUSA, projetos=PROJETOS, contagem=CONTAGEM)


def executar() -> int:
    # A ALBA tem 63 cadeiras: lista curta é falha da fonte.
    return ple.gravar(coletar(date.today()), fonte=FONTE, uf="BA", sigla="ALBA", url=API, minimo=50)


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
