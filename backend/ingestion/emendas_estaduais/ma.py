"""Emendas de deputados estaduais do Maranhão (Portal da Transparência do MA).

Fonte: a consulta "Emendas Parlamentares Estaduais" do Portal da Transparência do Maranhão
(transparencia.ma.gov.br/app/v2/emendasestaduais) tem o botão "Exportar CSV"
(`/app/v2/emendasestaduais/export?formato=csv`): uma linha por solicitação de emenda, com
número da emenda, exercício, parlamentar, modalidade, unidade gestora, empenhos, entidade
beneficiada, localizador do gasto (município), objeto, ação, valor solicitado, repasse,
pré-empenhado, empenhado, liquidado, pago e CNPJ do favorecido. Sem login nem captcha.

Armadilhas (amostra de 21/10/2026, 937 linhas):
- só o exercício de 2026 está na consulta (o filtro de ano só oferece 2026, e a exportação
  ignora o filtro);
- valores com ponto decimal, sem separador de milhar ("1000000", "1234.56"); vazio quando
  ainda não houve a etapa;
- CSV com vírgula, aspas em todos os campos, UTF-8 com BOM.
"""

import csv
import io
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "transparencia_ma_emendas"
UF = "MA"
URL = "https://www.transparencia.ma.gov.br/app/v2/emendasestaduais/export?formato=csv"
PAGINA = "https://www.transparencia.ma.gov.br/app/v2/emendasestaduais"
FONTE_NOME = "Emendas Parlamentares Estaduais (Portal da Transparência do Maranhão)"
CASA = "Assembleia Legislativa do Maranhão (ALEMA)"
MINIMO = 300  # eram 937 solicitações (só 2026) em 21/10/2026
ARQUIVO = "emendas.csv"
SITUACOES_FORA: tuple[str, ...] = ()
RECORTE = (
    "Emendas de deputados estaduais do orçamento de 2026, uma linha por solicitação, como o "
    "Portal da Transparência do Maranhão publica; anos anteriores não estão na consulta. Na "
    "compra feita pelo próprio Estado (aplicação direta), quem aparece como favorecido é o "
    "fornecedor. O município é o localizador do gasto."
)
TERMOS = (
    "Previsto: valor solicitado pelo deputado. Empenhado: reservado no orçamento. Pago: pago "
    "pelo Estado."
)


def _valor(texto: str | None) -> Decimal | None:
    """Ponto é sempre decimal nesta fonte ('1234.56'); vazio: None."""
    t = (texto or "").strip()
    if not t:
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return base.valor(t)


def ler(conteudo: bytes) -> list[dict[str, Any]]:
    linhas = []
    texto = conteudo.decode("utf-8-sig")
    for x in csv.DictReader(io.StringIO(texto, newline="")):
        chave = (x.get("Solicitação") or "").strip()
        if not chave:
            continue
        doc = base.so_digitos(x.get("Código Favorecido"))
        nome = base.texto(x.get("Entidade Beneficiada"))
        if len(doc) == 11:  # pessoa física: sem nome nem CPF (coleta mínima)
            nome = None
        linhas.append(
            {
                "ano": int(x["Exercício"]),
                "codigo": base.texto(x.get("Número Emenda")) or chave,
                "proposta": chave,
                "transferencia": base.texto((x.get("Empenhos") or "").split(",")[0]),
                "tipo": None,
                "autor_nome": base.texto(x.get("Parlamentar")) or "",
                "municipio_nome": base.texto(x.get("Localizador de Gasto")) or "",
                "municipio_ibge": None,
                "favorecido_nome": nome,
                "favorecido_cnpj": base.cnpj(doc),
                "favorecido_natureza": "Pessoa física" if len(doc) == 11 else None,
                "orgao": base.texto(x.get("Nome UG")),
                "instrumento": base.texto(x.get("Modalidade")),
                "objeto": base.sem_cpf(base.texto(x.get("Objeto"))),
                "situacao_proposta": base.texto(x.get("Tipo")),
                "situacao_transferencia": None,
                "valor_previsto": _valor(x.get("Valor Solicitado")) or Decimal(0),
                "valor_empenhado": _valor(x.get("Valor Empenhado")),
                "valor_pago": _valor(x.get("Valor Pago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    return ler(base.desempacotar(pacote)[ARQUIVO])


def baixar(client: httpx.Client) -> bytes:
    return base.empacotar({ARQUIVO: comum.get_bytes(client, URL)})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
