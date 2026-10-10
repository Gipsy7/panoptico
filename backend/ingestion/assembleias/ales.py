"""Assembleia Legislativa do Espírito Santo (ALES): deputados no cargo hoje, proposições de
autoria e presença em plenário, pela API pública do Processo Legislativo Eletrônico (o mesmo
sistema da ALBA, hospedado em www3.al.es.gov.br; ver `ple.py`).

- `/api/publico/parlamentar/`: 35 registros (30 "Ativos"; os outros são suplentes que não
  assumiram e titulares que saíram), com a frequência em plenário por ano.
- `/api/publico/proposicao/?ano=AAAA&sigla=XX`: a API aceita filtrar por sigla, e é
  necessário: o ano tem ~5.400 documentos (ofícios, atas, pautas) e cada página de 100 leva
  vários segundos. Projetos (lei, lei complementar, PEC, decreto legislativo e resolução)
  entram com a ementa; indicações e requerimentos, só como contagem.

Sem votos nominais (só o boletim de votação em PDF) e sem verba de gabinete nos dados abertos.
"""

import argparse
from datetime import date

from ingestion.assembleias import ple

FONTE = "ales"
SITE = "https://www3.al.es.gov.br/"
API = SITE + "api/publico/"
PAUSA = 1.0
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PR": "Projeto de Resolução",
}
CONTAGEM = {
    "IND": "Indicação",
    "REQ": "Requerimento",
    "RQI": "Requerimento de Informação",
}


def coletar(hoje: date) -> dict:
    return ple.coletar(
        hoje,
        site="https://www.al.es.gov.br/Deputado/Lista",
        api=API,
        pausa=PAUSA,
        projetos=PROJETOS,
        contagem=CONTAGEM,
        por_sigla=True,
    )


def executar() -> int:
    # A ALES tem 30 cadeiras: lista curta é falha da fonte.
    return ple.gravar(coletar(date.today()), fonte=FONTE, uf="ES", sigla="ALES", url=API, minimo=25)


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
