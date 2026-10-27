"""Emendas de deputados estaduais da Bahia (SEFAZ/BA, FIPLAN).

Fonte: o conjunto "Emendas Parlamentares Estaduais" do portal de dados abertos da Bahia
(dados.ba.gov.br/dataset/emendas-parlamentares, SEFAZ, dados do FIPLAN atualizados todo
dia): um zip com as visões do painel de emendas impositivas. Usamos a de despesas
(`VW_PAINEL_EMENDAS_PARLAMENTARES_DESPESAS.csv`): uma linha por emenda no orçamento (código
da dotação), com deputado autor, órgão, unidade, ação, valor orçado inicial e atual,
empenhado, liquidado e pago. Desde 2017. Sem login nem captcha.

O que a fonte **não** traz: município e beneficiário. Os pagamentos (outra visão do zip)
têm só o credor, que na execução pelo Estado é o fornecedor (ex.: fábrica de caixas d'água),
não a cidade nem a entidade atendida. Por isso as emendas da Bahia aparecem na página do
deputado, mas não na página da cidade.

Armadilhas (amostra de 21/10/2026):
- o nome do deputado vem com espaços à esquerda ("  Bobô");
- UTF-8 com BOM, `;`, aspas em todos os campos, vírgula decimal;
- o servidor manda a cadeia de certificados incompleta: a verificação TLS não é desligada;
  o intermediário que falta é baixado do endereço indicado no próprio certificado (ver
  `contexto_tls`);
- o conjunto "Transferências Especiais" do mesmo portal é de emendas **federais** recebidas
  pelo Estado (tem "Ministério de Origem"): não entra aqui.
"""

import csv
import io
import ssl
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import certifi
import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "sefaz_ba_emendas"
UF = "BA"
URL = (
    "https://dados.ba.gov.br/dataset/1436b3e7-6594-4683-bfa5-b2e3a6c69e07/resource/"
    "2d284f2e-79cc-4e3c-a45b-6fc903a6e2d0/download/emendasparlamentares.zip"
)
PAGINA = "https://dados.ba.gov.br/dataset/emendas-parlamentares"
# O servidor dados.ba.gov.br manda os intermediários errados (em 21/10/2026: "Sectigo RSA
# Domain/Organization Validation", não o "Sectigo Public Server Authentication CA OV R36" que
# assinou o certificado dele) e a verificação falha fora do navegador. Este é o intermediário
# certo, no endereço que o próprio certificado indica (Authority Information Access).
INTERMEDIARIO = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"
FONTE_NOME = "Emendas Parlamentares Estaduais (Secretaria da Fazenda da BA, FIPLAN)"
CASA = "Assembleia Legislativa da Bahia (ALBA)"
MINIMO = 2000  # eram 5.703 linhas em 21/10/2026
TEM_MUNICIPIO = False  # a fonte não traz município: só na página do deputado
ARQUIVO = "VW_PAINEL_EMENDAS_PARLAMENTARES_DESPESAS.csv"
SITUACOES_FORA: tuple[str, ...] = ()
RECORTE = (
    "Emendas impositivas de deputados estaduais no orçamento do Estado desde 2017, uma linha "
    "por emenda. A fonte não informa a cidade nem quem recebeu o dinheiro: por isso estas "
    "emendas aparecem só na página do deputado."
)
TERMOS = (
    "Previsto: valor atual da emenda no orçamento (depois de alterações). Empenhado: "
    "reservado no orçamento. Pago: pago pelo Estado no orçamento do ano."
)


def ler(conteudo: bytes) -> list[dict[str, Any]]:
    linhas = []
    texto = conteudo.decode("utf-8-sig")
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        codigo = x["num_codigo"].strip()
        linhas.append(
            {
                "ano": int(x["Ano Exercício"]),
                "codigo": codigo,
                "proposta": codigo,
                "transferencia": None,
                "tipo": None,
                "autor_nome": base.texto(x["Nome do Deputado"] or x["Deputado"]) or "",
                "municipio_nome": "",
                "municipio_ibge": None,
                "favorecido_nome": None,
                "favorecido_cnpj": None,
                "favorecido_natureza": None,
                "orgao": base.texto(x["Órgão"]),
                "instrumento": base.texto(x["Unidade Orçamentária"]),
                "objeto": base.texto(x["Ação do Programa de Governo"]),
                "situacao_proposta": None,
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x["Valor Orçado Atual."]) or Decimal(0),
                "valor_empenhado": base.valor(x["Valor Empenhado."]),
                "valor_pago": base.valor(x["Valor Pago."]) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    """Bruto: o zip da SEFAZ como veio (com todas as visões); lê só a de despesas."""
    return ler(base.desempacotar(pacote)[ARQUIVO])


def contexto_tls(intermediario_der: bytes) -> ssl.SSLContext:
    """Verificação TLS normal (raízes do certifi) com o certificado intermediário que o
    servidor deixa de enviar. O intermediário não é raiz: a cadeia ainda precisa chegar a uma
    autoridade raiz confiável, então a verificação continua inteira."""
    contexto = ssl.create_default_context(cafile=certifi.where())
    contexto.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(intermediario_der))
    return contexto


def baixar(client: httpx.Client) -> bytes:
    intermediario = comum.get_bytes(client, INTERMEDIARIO)
    with httpx.Client(
        timeout=client.timeout,
        headers=client.headers,
        follow_redirects=True,
        # Só IPv4, como em comum.criar_cliente (runners do GitHub sem rota IPv6).
        transport=httpx.HTTPTransport(local_address="0.0.0.0", verify=contexto_tls(intermediario)),
    ) as seguro:
        return comum.get_bytes(seguro, URL)


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
