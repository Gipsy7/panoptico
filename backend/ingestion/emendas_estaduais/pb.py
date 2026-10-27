"""Emendas de deputados estaduais da Paraíba (API de dados abertos do Estado).

Fonte: a API de dados abertos da Paraíba (api.dados.pb.gov.br, CGE/Codata), operação
"Consulta execução de emendas parlamentares impositivas"
(`/api/v1/orcamento/execucao_emendas?ano=AAAA&page=1&per_page=1000`), a mesma base da página
"Emendas Parlamentares" do Portal da Transparência (transparencia.pb.gov.br). Uma linha por
emenda × órgão × classificação da despesa (ação, natureza, fonte, modalidade): autor, número
da emenda, órgão, ação, valor da emenda, empenhado, liquidado e pago. Sem login nem captcha
(a chave `BearerAuth` do swagger é só das operações administrativas).

Armadilhas (amostra de 27/10/2026, 2021 a 2026):
- anos sem dado respondem 404 com "Nenhum registro encontrado" (antes de 2021);
- a mesma emenda pode ter mais de uma linha (outro órgão ou natureza), cada uma com o seu
  valor: o código mostrado leva um número de ordem ("0019/2025 (2)") para o previsto somar
  por linha; nenhuma linha se repete em todos os campos;
- não há município nem favorecido estruturados (a cidade às vezes está no texto do objeto,
  em outra operação): a emenda aparece só na página do deputado, como na Bahia;
- autor com o nome civil e, às vezes, o apelido entre parênteses
  ("JACI SEVERINO DE SOUZA (GALEGO SOUZA)");
- a página do portal lê a mesma base por um proxy próprio (`/api/execucao-emendas`) que
  responde 403 a leitura automática: não usamos; a API de dados abertos é a via publicada.
"""

import hashlib
import json
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "dadospb_emendas"
UF = "PB"
API = "https://api.dados.pb.gov.br/api/v1/orcamento/execucao_emendas"
URL = f"{API}?ano={{ano}}"
PAGINA = "https://transparencia.pb.gov.br/emendas-parlamentares"
FONTE_NOME = "Execução de emendas parlamentares impositivas (dados abertos da Paraíba)"
CASA = "Assembleia Legislativa da Paraíba (ALPB)"
PRIMEIRO_ANO = 2021
MINIMO = 1500  # eram 3.522 linhas de 2021 a 2026 em 27/10/2026
POR_PAGINA = 1000
PAUSA = 0.5
ARQUIVO = "execucao.json"
SITUACOES_FORA: tuple[str, ...] = ()
TEM_MUNICIPIO = False  # a fonte não informa a cidade
VALORES = ("valorEmenda", "valorEmpenhado", "valorLiquidado", "valorPago")
RECORTE = (
    "Emendas impositivas de deputados estaduais desde 2021, uma linha por emenda e "
    "classificação da despesa, como a API de dados abertos da Paraíba publica. A fonte não "
    "informa a cidade nem quem recebeu: as emendas aparecem só na página do deputado."
)
TERMOS = "Previsto: valor da emenda. Empenhado: reservado no orçamento. Pago: pago pelo Estado."


def ler(linhas_json: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = []
    ordem: dict[tuple[int, str], int] = {}
    # Ordem estável dentro da emenda: pelo resumo dos campos que não são valor.
    resumos = []
    for x in linhas_json:
        campos = {k: v for k, v in x.items() if k not in VALORES}
        resumo = hashlib.sha1(
            json.dumps(campos, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:12]
        resumos.append((int(x["ano"]), str(x["emenda"]).strip(), resumo, x))
    for ano, emenda, resumo, x in sorted(resumos, key=lambda r: r[:3]):
        n = ordem[(ano, emenda)] = ordem.get((ano, emenda), 0) + 1
        linhas.append(
            {
                "ano": ano,
                "codigo": emenda if n == 1 else f"{emenda} ({n})",
                "proposta": f"{ano}:{emenda}:{resumo}",
                "transferencia": None,
                "tipo": None,
                "autor_nome": base.texto(x.get("nomeAutor")) or "",
                "municipio_nome": "",
                "municipio_ibge": None,
                "favorecido_nome": None,
                "favorecido_cnpj": None,
                "favorecido_natureza": base.texto(x.get("modalidadeAplicacao")),
                "orgao": base.texto(x.get("unidadeOrcamentaria") or x.get("nomeOrgao")),
                "instrumento": base.texto(x.get("elementoDespesa")),
                "objeto": base.sem_cpf(base.texto(x.get("acao"))),
                "situacao_proposta": None,
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x.get("valorEmenda")) or Decimal(0),
                "valor_empenhado": base.valor(x.get("valorEmpenhado")),
                "valor_pago": base.valor(x.get("valorPago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    # parse_float=Decimal: os valores vêm como número no JSON e não podem passar por float.
    return ler(json.loads(base.desempacotar(pacote)[ARQUIVO], parse_float=Decimal))


def _ano(client: httpx.Client, ano: int) -> list[dict[str, Any]]:
    linhas: list[dict[str, Any]] = []
    pagina, paginas = 1, 1
    while pagina <= paginas:
        try:
            dados = comum.get_json(
                client, API, params={"ano": ano, "page": pagina, "per_page": POR_PAGINA}
            )
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code == 404 and pagina == 1:
                return []  # ano sem registro
            raise
        paginas = int(dados["paginacao"]["pages"])
        total = int(dados["paginacao"]["total"])
        linhas += dados["dados"]
        pagina += 1
        time.sleep(PAUSA)
    if len(linhas) != total:
        raise ValueError(f"{FONTE}: {len(linhas)} de {total} linhas de {ano}; abortando.")
    return linhas


def baixar(client: httpx.Client) -> bytes:
    linhas: list[dict[str, Any]] = []
    for ano in range(PRIMEIRO_ANO, date.today().year + 1):
        do_ano = _ano(client, ano)
        if not do_ano:
            raise ValueError(f"{FONTE}: nenhuma emenda de {ano}; abortando.")
        linhas += do_ano
    conteudo = json.dumps(linhas, ensure_ascii=False).encode()
    return base.empacotar({ARQUIVO: conteudo})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
