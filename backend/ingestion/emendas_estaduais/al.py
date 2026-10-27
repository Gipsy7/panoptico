"""Emendas de deputados estaduais de Alagoas (Portal da Transparência de AL).

Fonte: a consulta "Emendas Parlamentares Estaduais" do Portal da Transparência de Alagoas
(transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais) preenche a tabela com um
JSON público (`/despesa/json-emendas-parlamentares/`, paginado por `limit` e `offset`), uma
linha por emenda: parlamentar, partido, código da emenda, município e localidade,
beneficiário, objeto, forma de repasse, dotação inicial e atualizada, empenhado, liquidado e
pago. Sem login nem captcha.

Armadilhas (amostra de 21/10/2026):
- só há o orçamento de 2026 (376 emendas); o filtro `ano` com outros anos devolve zero;
- valores em texto com vírgula decimal ("338.029,26");
- o CNPJ do beneficiário não tem campo próprio: às vezes vem no fim do objeto
  ("...MARECHAL DEODORO-11294109000103"); não é extraído.
"""

import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "transparencia_al_emendas"
UF = "AL"
URL = "https://transparencia.al.gov.br/despesa/json-emendas-parlamentares/"
PAGINA = "https://transparencia.al.gov.br/despesa/emendas-parlamentares-estaduais"
FONTE_NOME = "Emendas Parlamentares Estaduais (Portal da Transparência de Alagoas)"
CASA = "Assembleia Legislativa de Alagoas (ALE)"
MINIMO = 100  # eram 376 emendas (só 2026) em 21/10/2026
POR_PAGINA = 200
PAUSA = 1.0
ARQUIVO = "emendas.json"
SITUACOES_FORA: tuple[str, ...] = ()
RECORTE = (
    "Emendas de deputados estaduais do orçamento de 2026, uma linha por emenda, como o "
    "Portal da Transparência de Alagoas publica; anos anteriores não estão na consulta. O "
    "município é o da emenda."
)
TERMOS = (
    "Previsto: dotação atualizada da emenda. Empenhado: reservado no orçamento. Pago: pago "
    "pelo Estado."
)


def ler(linhas_json: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = []
    for x in linhas_json:
        chave = str(x["idt_emenda_despesa"])
        linhas.append(
            {
                "ano": int(x["ano"]),
                "codigo": base.texto(x.get("codigo_identificador_emenda")) or chave,
                "proposta": chave,
                "transferencia": base.texto(x.get("numero_convenio")),
                "tipo": None,
                "autor_nome": base.texto(x.get("parlamentar")) or "",
                "municipio_nome": base.texto(x.get("municipio") or x.get("localidade")) or "",
                "municipio_ibge": None,
                "favorecido_nome": base.texto(x.get("beneficiario")),
                "favorecido_cnpj": None,
                "favorecido_natureza": base.texto(x.get("forma_repasse")),
                "orgao": base.texto(x.get("orgao_entidade_executora")),
                "instrumento": base.texto(x.get("forma_repasse")),
                "objeto": base.sem_cpf(base.texto(x.get("objeto_despesa"))),
                "situacao_proposta": base.texto(x.get("modalidade")),
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x.get("valor_dotacao_atualizado")) or Decimal(0),
                "valor_empenhado": base.valor(x.get("valor_empenhado")),
                "valor_pago": base.valor(x.get("valor_pago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    return ler(json.loads(base.desempacotar(pacote)[ARQUIVO]))


def baixar(client: httpx.Client) -> bytes:
    linhas: list[dict[str, Any]] = []
    total = None
    while total is None or len(linhas) < total:
        pagina = comum.get_json(client, URL, params={"limit": POR_PAGINA, "offset": len(linhas)})
        total = int(pagina["total"])
        if not pagina["rows"]:
            break
        linhas += pagina["rows"]
        time.sleep(PAUSA)
    if total is not None and len(linhas) != total:
        raise ValueError(f"{FONTE}: {len(linhas)} de {total} emendas baixadas; abortando.")
    conteudo = json.dumps(linhas, ensure_ascii=False, sort_keys=True).encode()
    return base.empacotar({ARQUIVO: conteudo})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
