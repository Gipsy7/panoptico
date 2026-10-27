"""Emendas de deputados estaduais de Sergipe (Portal da Transparência de SE).

Fonte: a página "Emendas Estaduais" do Portal da Transparência de Sergipe
(transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais) lê uma API pública
(`api.transparencia.se.gov.br/api/emendas-estaduais?ano=AAAA&page=N&limit=100`; os anos
disponíveis em `/emendas-estaduais/anos`), uma linha por emenda: exercício, órgão,
parlamentar, objeto, executor (nome e CNPJ no mesmo texto), localidade, ação, grupo de
despesa, valor indicado e valor pago. Sem login nem captcha.

Armadilhas (amostra de 21/10/2026, 2022 a 2025):
- não há número da emenda nem identificador da linha: a chave é o ano com um resumo (sha1)
  do conteúdo da linha, e linhas idênticas recebem um contador;
- não há valor empenhado;
- valores com espaços e ponto de milhar sem decimais (" 200.000 "); pago vazio quando ainda
  não houve pagamento;
- o `limit` máximo é 100 por página;
- "executor" é o órgão ou entidade que executa, com o CNPJ no texto
  ("CORPO DE BOMBEIROS ... CNPJ: 34.850.068/0001-81").
"""

import hashlib
import json
import re
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "transparencia_se_emendas"
UF = "SE"
API = "https://api.transparencia.se.gov.br/api/emendas-estaduais"
URL = f"{API}?ano={{ano}}"
PAGINA = "https://www.transparencia.se.gov.br/EmendasParlamentares/EmendasEstaduais"
FONTE_NOME = "Emendas Estaduais (Portal da Transparência de Sergipe)"
CASA = "Assembleia Legislativa de Sergipe (ALESE)"
MINIMO = 800  # eram 2.202 emendas de 2022 a 2025 em 21/10/2026
POR_PAGINA = 100
PAUSA = 0.5
ARQUIVO = "emendas.json"
SITUACOES_FORA: tuple[str, ...] = ()
TEM_EMPENHADO = False  # a fonte não publica o empenhado
CNPJ_NO_TEXTO = re.compile(r"\s*-?\s*CNPJ:?\s*([\d./-]+)\s*$", re.I)
RECORTE = (
    "Emendas de deputados estaduais desde 2022, uma linha por emenda, como o Portal da "
    "Transparência de Sergipe publica. A fonte não informa o valor empenhado. O município é "
    "a localidade da emenda."
)
TERMOS = "Previsto: valor indicado pelo deputado. Pago: pago pelo Estado."


def executor(texto: str | None) -> tuple[str | None, str | None]:
    """'NOME CNPJ: 34.850.068/0001-81' -> (nome, cnpj só com dígitos)."""
    t = base.texto(texto)
    if not t:
        return None, None
    achado = CNPJ_NO_TEXTO.search(t)
    if not achado:
        return t, None
    return base.texto(t[: achado.start()]), base.cnpj(achado.group(1))


def ler(linhas_json: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = []
    contagem: dict[str, int] = {}
    for x in linhas_json:
        ano = int(x["exercicio"])
        resumo = hashlib.sha1(
            json.dumps(x, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:12]
        chave = f"{ano}:{resumo}"
        contagem[chave] = contagem.get(chave, 0) + 1
        chave = f"{chave}:{contagem[chave]}"
        nome, cnpj = executor(x.get("executor"))
        linhas.append(
            {
                "ano": ano,
                "codigo": chave,
                "proposta": chave,
                "transferencia": None,
                "tipo": None,
                "autor_nome": base.texto(x.get("parlamentar")) or "",
                "municipio_nome": base.texto(x.get("localidade")) or "",
                "municipio_ibge": None,
                "favorecido_nome": nome,
                "favorecido_cnpj": cnpj,
                "favorecido_natureza": None,
                "orgao": base.texto(x.get("orgaoProcessador")),
                "instrumento": base.texto(x.get("gnd")),
                "objeto": base.sem_cpf(base.texto(x.get("descricaoObjeto"))),
                "situacao_proposta": None,
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x.get("valorIndicado")) or Decimal(0),
                "valor_empenhado": None,
                "valor_pago": base.valor(x.get("valorPago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    return ler(json.loads(base.desempacotar(pacote)[ARQUIVO]))


def baixar(client: httpx.Client) -> bytes:
    linhas: list[dict[str, Any]] = []
    for ano in sorted(comum.get_json(client, f"{API}/anos")):
        pagina, total = 1, None
        do_ano: list[dict[str, Any]] = []
        while total is None or len(do_ano) < total:
            resposta = comum.get_json(
                client, API, params={"ano": ano, "page": pagina, "limit": POR_PAGINA}
            )
            total = int(resposta["total"])
            itens = resposta.get("data") or resposta.get("items") or []
            if not itens:
                break
            do_ano += itens
            pagina += 1
            time.sleep(PAUSA)
        if len(do_ano) != total:
            raise ValueError(f"{FONTE}: {len(do_ano)} de {total} emendas de {ano}; abortando.")
        linhas += do_ano
    conteudo = json.dumps(linhas, ensure_ascii=False).encode()
    return base.empacotar({ARQUIVO: conteudo})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
