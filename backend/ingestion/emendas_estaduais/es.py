"""Emendas de deputados estaduais do Espírito Santo (SEFAZ/ES, Portal da Transparência).

Fonte: o conjunto "[Portal da Transparência] Emendas Parlamentares do Estado" do portal de
dados abertos do ES (dados.es.gov.br, SEFAZ), um CSV por ano ("Emendas-Estaduais-AAAA.csv",
2021 em diante): uma linha por emenda × instrumento de execução (convênio, contrato ou
empenho), com autor ("Dep. Fulano"), número da emenda, objeto, município (código IBGE de 6
dígitos, sem o verificador), órgão executor, valor previsto da emenda, favorecido (CNPJ e
nome) e empenhado, liquidado e pago daquele instrumento. Os endereços dos arquivos mudam a
cada publicação: são lidos pela API do CKAN (`package_show`). Sem login nem captcha.

Armadilhas (amostra de 21/10/2026):
- o download redireciona para um link assinado no S3 do Estado que expira em 1 hora; numa
  das tentativas o link de 2025 deu 403 e, refeito, abriu: é falha passageira, não bloqueio;
- em 2023 e 2025 a mesma linha (emenda, instrumento, favorecido e valores) vem repetida
  com outro `Id`, mudando só o nome da ação ("APOIO À ..." e "PPA DE RAP - APOIO À ...");
  somadas, 160 emendas de 2023 e 206 de 2025 teriam pago acima do previsto. Fica uma;
- `ValorPrevisto` se repete em todas as linhas da emenda: soma-se uma vez por emenda;
- emenda ainda sem execução vem com favorecido e valores vazios;
- em "Aplicações diretas" o favorecido é o fornecedor (ex.: montadora de veículos), não quem
  recebe o bem: a natureza guarda a modalidade para não confundir;
- UTF-8 com BOM, `;`, vírgula decimal com quatro casas ("194000,0000").
"""

import csv
import io
import re
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "sefaz_es_emendas"
UF = "ES"
CKAN = "https://dados.es.gov.br/api/3/action/package_show"
CONJUNTO = "portal-da-transparencia-emendas-parlamentares-do-estado"
URL = f"{CKAN}?id={CONJUNTO}"
PAGINA = f"https://dados.es.gov.br/dataset/{CONJUNTO}"
FONTE_NOME = "Emendas Parlamentares do Estado (Secretaria da Fazenda do ES)"
CASA = "Assembleia Legislativa do Espírito Santo (ALES)"
PRIMEIRO_ANO = 2021
MINIMO = 3000  # eram 9.877 linhas de 2021 a 2026 em 21/10/2026
PAUSA = 1.0
SITUACOES_FORA: tuple[str, ...] = ()
VERSAO = 2  # 21/10/2026: linhas repetidas pela exportação entram uma vez
# Colunas que mudam quando a exportação repete a mesma linha (ver armadilhas).
REPETEM = ("Id", "DescricaoAcaoPPA")
ARQUIVO_ANO = re.compile(r"^emendas-estaduais-(\d{4})\.csv$", re.I)
RECORTE = (
    "Emendas de deputados estaduais aprovadas na Lei Orçamentária desde 2021, uma linha por "
    "emenda e instrumento de execução (convênio, contrato ou empenho). Na compra feita pelo "
    "próprio Estado (aplicação direta), quem aparece como favorecido é o fornecedor. O "
    "município é o informado na emenda."
)
TERMOS = (
    "Previsto: valor da emenda na Lei Orçamentária, contado uma vez. Empenhado: reservado no "
    "orçamento. Pago: pago pelo Estado (no ano da emenda)."
)


def ler(conteudo: bytes, ano_arquivo: int) -> list[dict[str, Any]]:
    linhas = []
    vistas: set[tuple[str, ...]] = set()
    texto = conteudo.decode("utf-8-sig")
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        assinatura = tuple(v for k, v in x.items() if k not in REPETEM)
        if assinatura in vistas:  # a mesma linha repetida com outro nome da ação
            continue
        vistas.add(assinatura)
        doc = base.so_digitos(x["CpfCnpjNis"])
        nome = base.texto(x["Favorecido"])
        natureza = base.texto(x["Modalidade"])
        if len(doc) == 11:  # pessoa física: sem nome nem CPF (coleta mínima)
            nome, natureza = None, "Pessoa física"
        codigo = " ".join((x["NumeroEmenda"] or "").split())
        linhas.append(
            {
                "ano": int(x["AnoEmenda"] or ano_arquivo),
                "codigo": codigo,
                "proposta": f"{ano_arquivo}:{x['Id'].strip()}",
                "transferencia": base.texto(x["NumeroInstrumento"]),
                "tipo": None,
                "autor_nome": base.texto(x["NomeAutor"]) or "",
                "municipio_nome": base.texto(x["Municipio"]) or "",
                "municipio_ibge": base.so_digitos(x["CodigoMunicipio"]) or None,
                "favorecido_nome": nome,
                "favorecido_cnpj": base.cnpj(doc),
                "favorecido_natureza": natureza,
                "orgao": base.texto(x["DescricaoOrgaoExecutor"]),
                "instrumento": base.texto(x["Modalidade"]),
                "objeto": base.sem_cpf(base.texto(x["ObjetoFinalidade"])),
                "situacao_proposta": base.texto(x["NomeElemento"]),
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x["ValorPrevisto"]) or Decimal(0),
                "valor_empenhado": base.valor(x["ValorEmpenho"]),
                "valor_pago": base.valor(x["ValorPago"]) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    linhas = []
    for nome, conteudo in sorted(base.desempacotar(pacote).items()):
        achado = ARQUIVO_ANO.match(nome)
        if achado:
            linhas += ler(conteudo, int(achado.group(1)))
    return linhas


def arquivos_por_ano(pacote_ckan: dict) -> dict[int, str]:
    """Resposta do package_show -> {ano: URL do CSV de emendas do ano} (sem os de execução,
    contratos e convênios)."""
    saida = {}
    for r in pacote_ckan["result"]["resources"]:
        nome = (r.get("url") or "").rsplit("/", 1)[-1]
        achado = ARQUIVO_ANO.match(nome)
        if achado and int(achado.group(1)) >= PRIMEIRO_ANO:
            saida[int(achado.group(1))] = r["url"]
    return saida


def baixar(client: httpx.Client, hoje: date | None = None) -> bytes:
    urls = arquivos_por_ano(comum.get_json(client, CKAN, params={"id": CONJUNTO}))
    hoje = hoje or date.today()
    faltam = [a for a in range(PRIMEIRO_ANO, hoje.year + 1) if a not in urls]
    if faltam:
        raise ValueError(f"{FONTE}: sem arquivo de emendas para {faltam}; abortando.")
    arquivos = {}
    for ano, url in sorted(urls.items()):
        time.sleep(PAUSA)
        conteudo = comum.get_bytes(client, url)
        if conteudo.lstrip()[:15].lower().startswith(b"<!doctype"):
            raise ValueError(f"{FONTE}: o arquivo de {ano} veio como página HTML; abortando.")
        arquivos[f"emendas-estaduais-{ano}.csv"] = conteudo
    return base.empacotar(arquivos)


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
