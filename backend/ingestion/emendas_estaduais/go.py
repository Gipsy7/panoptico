"""Emendas de deputados estaduais de Goiás (dados abertos do Estado, só 2023).

Fonte: o conjunto "Emendas Parlamentares" do portal de dados abertos de Goiás
(dadosabertos.go.gov.br/dataset/emendas-parlamentares), um arquivo por ano. Só o de 2023
("emendas_parlamentares_ano_2023.zip", um CSV) é carregado: uma linha por emenda ×
processo × beneficiário, com órgão, função, número da emenda, autor, objeto, município,
beneficiário (nome e CNPJ) e valores previsto, empenhado, liquidado e pago. O endereço do
arquivo é lido pela API do CKAN (`package_show`). Sem login nem captcha.

Por que só 2023 (conferido em 27/10/2026; ver docs/emendas_estaduais_levantamento.md):
- 2024 e 2025 (até julho) saíram de planilha com o número do empenho, do processo e o CNPJ
  em notação científica ("2,02419E+15", "7,99205E+11"): o empenho tem só 5 valores
  distintos em 2.594 linhas, e o arquivo de 2025 repete o empenho por parcela sem chave
  para tirar a repetição. Não há como recuperar a chave nem o documento;
- 2021 e 2022 não têm município e trazem a posição de execução de 06/2022 e 02/2023 (o
  pago de 2022 ficou em R$ 107 milhões de R$ 342 milhões empenhados);
- 2019 e 2020 só têm o valor da emenda, sem execução.

Armadilhas do arquivo de 2023:
- latin-1, `;`, valores sem milhar e com vírgula decimal só às vezes ("300000",
  "432356704,5");
- duas linhas de rodapé: "Total" (soma das colunas) e "Filtros aplicados"; a soma das
  linhas é conferida com o "Total" e a carga aborta se não bater;
- o número da emenda se repete (uma linha por processo e beneficiário), cada linha com o
  seu previsto (que soma o "Total"): a chave é por linha;
- o CNPJ perdeu os zeros à esquerda ("1112580000171"): volta a 14 dígitos só se o dígito
  verificador conferir; número de 11 dígitos que seja CPF válido não é guardado, nem o nome;
- dois municípios com o nome por extenso ("CIDADE DE GOIAS" é Goiás, "CAMPOS VERDES DE GOIAS"
  é Campos Verdes): código IBGE fixado abaixo; "LARANJEIRAS" (2 linhas) não é município de
  GO e fica sem cidade.
"""

import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "dadosabertos_go_emendas"
UF = "GO"
CKAN = "https://dadosabertos.go.gov.br/api/3/action/package_show"
CONJUNTO = "emendas-parlamentares"
URL = f"{CKAN}?id={CONJUNTO}"
PAGINA = f"https://dadosabertos.go.gov.br/dataset/{CONJUNTO}"
FONTE_NOME = "Emendas Parlamentares (Portal de Dados Abertos de Goiás)"
CASA = "Assembleia Legislativa de Goiás (Alego)"
ANO = 2023
ARQUIVO = re.compile(rf"emendas_parlamentares_ano_{ANO}\.zip$", re.I)
MINIMO = 1000  # eram 1.924 linhas de 2023 em 27/10/2026
SITUACOES_FORA: tuple[str, ...] = ()
# Nome por extenso no arquivo -> código IBGE (conferido na tabela do IBGE).
MUNICIPIOS = {"CIDADE DE GOIAS": "5208905", "CAMPOS VERDES DE GOIAS": "5204953"}
RECORTE = (
    "Só as emendas de deputados estaduais de 2023, uma linha por emenda, processo e "
    "beneficiário, como o portal de dados abertos de Goiás publica. Os arquivos de 2024 e "
    "2025 trazem o número do empenho e o CNPJ corrompidos pela planilha, e os anteriores não "
    "trazem a cidade ou a execução; pedimos os arquivos corrigidos."
)
TERMOS = (
    "Previsto: valor da emenda. Empenhado: reservado no orçamento. Pago: pago pelo Estado "
    "(posição do arquivo publicado em fevereiro de 2025)."
)


def _dv(numeros: str, pesos: list[int]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(d: str) -> bool:
    if len(d) != 14 or len(set(d)) == 1:
        return False
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _dv(d[:12], p1) == d[12] and _dv(d[:13], [6, *p1]) == d[13]


def cpf_valido(d: str) -> bool:
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for i in (9, 10):
        soma = sum(int(d[j]) * (i + 1 - j) for j in range(i))
        if str(soma * 10 % 11 % 10) != d[i]:
            return False
    return True


def documento(x: str | None) -> tuple[str | None, bool]:
    """(CNPJ com os zeros à esquerda devolvidos, é CPF?). CNPJ só se o verificador conferir."""
    d = base.so_digitos(x)
    if not d:
        return None, False
    if len(d) == 11 and cpf_valido(d):
        return None, True
    completo = d.zfill(14)
    return (completo if len(d) <= 14 and cnpj_valido(completo) else None), False


def ler(conteudo: bytes) -> list[dict[str, Any]]:
    texto = conteudo.decode("latin-1")
    linhas: list[dict[str, Any]] = []
    total: dict[str, Any] | None = None
    contagem: dict[str, int] = {}
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        ano = (x.get("Ano Emenda") or "").strip()
        if ano == "Total":
            total = x
            continue
        if ano != str(ANO):  # linha em branco e "Filtros aplicados" do rodapé
            continue
        numero = (x["Nº Emenda"] or "").strip()
        resumo = hashlib.sha1(
            json.dumps(x, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:12]
        chave = f"{ANO}-{numero}:{resumo}"
        contagem[chave] = contagem.get(chave, 0) + 1
        chave = f"{chave}:{contagem[chave]}"
        cnpj, pessoa_fisica = documento(x["CNPJ do Beneficiário"])
        municipio = base.texto(x["Município"]) or ""
        linhas.append(
            {
                "ano": ANO,
                "codigo": chave,
                "proposta": chave,
                "transferencia": base.texto(x["Nº Processo"]),
                "tipo": None,
                "autor_nome": base.texto(x["Autor da Emenda"]) or "",
                "municipio_nome": municipio,
                "municipio_ibge": MUNICIPIOS.get(municipio),
                "favorecido_nome": None if pessoa_fisica else base.texto(x["Beneficiário"]),
                "favorecido_cnpj": cnpj,
                "favorecido_natureza": "Pessoa física" if pessoa_fisica else None,
                "orgao": base.texto(x["Orgão"]),
                "instrumento": base.texto(x["Função (Área)"]),
                "objeto": base.sem_cpf(base.texto(x["Objeto"])),
                "situacao_proposta": None,
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x["Valor Previsto (R$)"]) or Decimal(0),
                "valor_empenhado": base.valor(x["Valor Empenho (R$)"]),
                "valor_pago": base.valor(x["Valor Pago (R$)"]) or Decimal(0),
            }
        )
    if total is None:
        raise ValueError(f"{FONTE}: sem a linha 'Total' para conferir; abortando.")
    for coluna, campo in (
        ("Valor Previsto (R$)", "valor_previsto"),
        ("Valor Empenho (R$)", "valor_empenhado"),
        ("Valor Pago (R$)", "valor_pago"),
    ):
        soma = sum((x[campo] or Decimal(0) for x in linhas), Decimal(0))
        esperado = base.valor(total[coluna]) or Decimal(0)
        if abs(soma - esperado) > Decimal("0.1"):  # o "Total" vem com uma casa às vezes
            raise ValueError(f"{FONTE}: {coluna} soma {soma}, o arquivo diz {esperado}.")
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(nomes) != 1:
            raise ValueError(f"{FONTE}: esperava um CSV no zip, veio {nomes}.")
        return ler(z.read(nomes[0]))


def url_do_arquivo(pacote_ckan: dict) -> str:
    for r in pacote_ckan["result"]["resources"]:
        if ARQUIVO.search(r.get("url") or ""):
            return r["url"]
    raise ValueError(f"{FONTE}: arquivo de {ANO} não está mais no conjunto; abortando.")


def baixar(client: httpx.Client) -> bytes:
    url = url_do_arquivo(comum.get_json(client, CKAN, params={"id": CONJUNTO}))
    return comum.get_bytes(client, url)


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
