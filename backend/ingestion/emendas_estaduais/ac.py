"""Emendas de deputados estaduais do Acre (SEPLAN/AC, Portal de Emendas Estaduais).

Fonte: a tabela da página "Emendas Parlamentares Estaduais" da Secretaria de Planejamento
(seplan.ac.gov.br/gestao-de-recursos/convenios/emendas-parlamentares-estaduais/, a mesma que o
Portal da Transparência do Acre mostra) é lida pela própria página de uma planilha publicada
em CSV (Google Sheets "publicar na web"). Uma linha por emenda, 2023 em diante, com
parlamentar, município, entidade beneficiada (nome e CNPJ), modalidade, objeto, órgão
concedente, valor da emenda, empenhado, liquidado e pago, situação e links do processo.
Sem login nem captcha.

Armadilhas (amostra de 21/10/2026, 2.890 linhas):
- números em dois formatos na mesma coluna: "300.000,00" e "300000";
- linhas em branco no fim (sem número de emenda): descartadas;
- a planilha traz agência e conta bancária do beneficiário e links de documentos: não são
  guardados (coleta mínima);
- CSV com vírgula como separador e aspas (exportação do Google Sheets), UTF-8.
"""

import csv
import io
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "seplan_ac_emendas"
UF = "AC"
URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRzbV0AT43iRHZEQ4ovc5jbywcxI2De6p_dYftLPku"
    "V3ZsiemRCdhjbhHE8pk_f_FnzHi9rM67PqyYh/pub?gid=1271042240&single=true&output=csv"
)
PAGINA = "https://seplan.ac.gov.br/gestao-de-recursos/convenios/emendas-parlamentares-estaduais/"
FONTE_NOME = "Emendas Parlamentares Estaduais (Secretaria de Planejamento do Acre)"
CASA = "Assembleia Legislativa do Acre (ALEAC)"
MINIMO = 1000  # eram 2.889 emendas em 21/10/2026
ARQUIVO = "emendas.csv"
PLANILHA = re.compile(r"https://docs\.google\.com/spreadsheets/d/e/[\w-]+/pub\?[^\"'\s]*output=csv")
SITUACOES_FORA: tuple[str, ...] = ()
RECORTE = (
    "Emendas de deputados estaduais desde 2023, uma linha por emenda, como a Secretaria de "
    "Planejamento publica: transferências a entidades sem fins lucrativos e a prefeituras e "
    "compras feitas pelo próprio Estado. O município é o da emenda."
)
TERMOS = "Previsto: valor da emenda. Empenhado: reservado no orçamento. Pago: pago pelo Estado."


def ler(conteudo: bytes) -> list[dict[str, Any]]:
    linhas = []
    texto = conteudo.decode("utf-8-sig")
    for x in csv.DictReader(io.StringIO(texto, newline="")):
        codigo = (x.get("N° Emenda") or "").strip()
        if not codigo or not (x.get("Parlamentar") or "").strip():
            continue
        doc = base.so_digitos(x.get("CNPJ Entidade Beneficiada"))
        nome = base.texto(x.get("Nome Entidade Beneficiada"))
        natureza = base.texto(x.get("Descrição Modalidade Aplicacao Estadual"))
        if len(doc) == 11:  # pessoa física: sem nome nem CPF (coleta mínima)
            nome, natureza = None, "Pessoa física"
        linhas.append(
            {
                "ano": int(x["Ano"]),
                "codigo": codigo,
                "proposta": codigo,
                "transferencia": base.texto(x.get("Número do Instrumento de Repasse")),
                "tipo": None,
                "autor_nome": base.texto(x["Parlamentar"]) or "",
                "municipio_nome": base.texto(x.get("Municípios")) or "",
                "municipio_ibge": None,
                "favorecido_nome": nome,
                "favorecido_cnpj": base.cnpj(doc),
                "favorecido_natureza": natureza,
                "orgao": base.texto(x.get("Concedente")),
                "instrumento": natureza,
                "objeto": base.sem_cpf(base.texto(x.get("Objeto da Emenda"))),
                "situacao_proposta": base.texto(x.get("Situação")),
                "situacao_transferencia": base.texto(x.get("Situação do Instrumento de Repasse")),
                "valor_previsto": base.valor(x.get("Valor Emenda")) or Decimal(0),
                "valor_empenhado": base.valor(x.get("Empenhado")),
                "valor_pago": base.valor(x.get("Pago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    return ler(base.desempacotar(pacote)[ARQUIVO])


def url_da_pagina(html: str) -> str | None:
    """O endereço da planilha que a página da SEPLAN usa (muda se ela republicar)."""
    achado = PLANILHA.search(html)
    return achado.group(0).replace("&amp;", "&") if achado else None


def baixar(client: httpx.Client) -> bytes:
    try:
        url = url_da_pagina(comum.get_bytes(client, PAGINA).decode("utf-8", "replace")) or URL
    except httpx.HTTPError:
        url = URL
    return base.empacotar({ARQUIVO: comum.get_bytes(client, url)})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
