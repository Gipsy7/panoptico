"""Despesas das prefeituras e câmaras do Rio Grande do Sul, dados abertos do TCE-RS.

Um arquivo por ano ("Despesa orçamentária por empenhos") com cada empenho, liquidação e
pagamento de todos os órgãos municipais (15 GB descompactado em 2025). É baixado para o
disco e lido em fluxo; guardamos só o total PAGO no ano por fornecedor, por município e
órgão (prefeitura, câmara, outros), e só os maiores fornecedores de cada órgão, como no
TCE-SP (mesmas regras em `tce.sp.linhas_para_gravar`).

O arquivo não traz o código IBGE: o órgão (`cd_orgao`) é ligado ao município pelo
cadastro de órgãos auditados do TCE-RS, que vai junto no bruto (dentro do mesmo zip).
"""

import argparse
import csv
import io
import re
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import DespesaFornecedor, FonteIngestao, Municipio
from ingestion import comum
from ingestion.tce import sp

FONTE = "tce_rs"
URL = "https://dados.tce.rs.gov.br/dados/municipal/empenhos/{ano}.csv.zip"
URL_ORGAOS = "https://dados.tce.rs.gov.br/dados/auxiliar/orgaos_auditados_rs.csv"
ORGAOS_NO_ZIP = "orgaos_auditados_rs.csv"

# SETOR_GOVERNAMENTAL do cadastro de órgãos. Consórcios intermunicipais ficam de fora:
# atendem vários municípios e só estão cadastrados na cidade-sede.
TIPOS = {"EXECUTIVO": "prefeitura", "LEGISLATIVO": "camara"}
FORA = {"CONSÓRCIO ADMINISTRATIVO"}

# Credor sem CNPJ com nome de folha ("FOLHA DE PAGAMENTO", "SERVIDORES MUNICIPAIS",
# "INATIVOS", "VEREADORES 17 LEGISLATURA", "F U N C I O N A R I O S"...).
PALAVRAS_FOLHA = re.compile(
    r"FOLHA|FUNCION|SERVIDOR|INATIVO|PENSIONIST|APOSENTAD|VENCIMENTO|VEREADOR|PESSOAL|"
    r"SALARI|REMUNERAC"
)
SIGLA_FOLHA = re.compile(r"\bFL[AS]\b")


def _digitos_ok(numero: str, pesos: list[int]) -> bool:
    for posicao in (len(pesos) - 1, len(pesos)):
        soma = sum(int(d) * p for d, p in zip(numero[:posicao], pesos[-posicao:], strict=True))
        resto = soma % 11
        if int(numero[posicao]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


def cnpj_valido(numero: str) -> bool:
    return (
        len(numero) == 14
        and len(set(numero)) > 1
        and _digitos_ok(numero, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    )


def cpf_valido(numero: str) -> bool:
    return (
        len(numero) == 11
        and len(set(numero)) > 1
        and _digitos_ok(numero, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    )


def ler_orgaos(conteudo: bytes) -> dict[str, tuple[str, str | None, str]]:
    """cd_orgao -> (IBGE, tipo de órgão ou None se fica de fora, CNPJ do órgão)."""
    orgaos = {}
    for linha in csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig"))):
        if linha["ESFERA"] != "MUNICIPAL":
            continue
        setor = linha["SETOR_GOVERNAMENTAL"].strip()
        tipo = None if setor in FORA else TIPOS.get(setor, "outros")
        cnpj = "".join(c for c in linha["CNPJ"] if c.isdigit()).zfill(14)
        orgaos[linha["CD_ORGAO"].strip()] = (linha["CD_MUNICIPIO_IBGE"].strip(), tipo, cnpj)
    return orgaos


def e_folha_sem_cnpj(credor: str) -> bool:
    chave = comum.chave_nome(credor)
    return bool(PALAVRAS_FOLHA.search(chave.replace(" ", "")) or SIGLA_FOLHA.search(chave))


def valor(texto: str) -> Decimal:
    try:
        return Decimal((texto or "0").strip())
    except InvalidOperation:
        return Decimal(0)


def agregar(
    linhas: Any, ano: int, orgaos: dict, fora: Counter | None = None
) -> dict[tuple[str, str], dict[tuple[str, str | None], list]]:
    """(ibge, órgão) -> {(fornecedor, CNPJ): [valor pago, nº de pagamentos]}.

    Só pagamentos (tipo_operacao "P") feitos no ano: o arquivo do ano traz também o
    histórico dos empenhos de anos anteriores (restos a pagar), com pagamentos antigos.
    `fora` acumula o valor que ficou de fora, por motivo."""
    fora = fora if fora is not None else Counter()
    soma: dict[tuple[str, str], dict[tuple[str, str | None], list]] = defaultdict(dict)
    ano_texto = str(ano)
    for linha in linhas:
        if linha.get("tipo_operacao") != "P" or linha.get("ano_operacao") != ano_texto:
            continue
        pago = valor(linha.get("vl_pagamento"))
        orgao = orgaos.get((linha.get("cd_orgao") or "").strip())
        if orgao is None:
            fora["órgão fora do cadastro municipal"] += pago
            continue
        ibge, tipo, cnpj_orgao = orgao
        if tipo is None:
            fora["consórcio intermunicipal"] += pago
            continue
        nome = " ".join((linha.get("nm_credor") or "Não identificado").split())[:300]
        documento = "".join(c for c in linha.get("cnpj_cpf") or "" if c.isdigit())
        if linha.get("tp_pessoa") == "PF" or (
            not cnpj_valido(documento.zfill(14)) and cpf_valido(documento)
        ):
            fornecedor = (sp.PESSOAS_FISICAS, None)
        elif documento and documento.zfill(14) == cnpj_orgao:
            fornecedor = (sp.FOLHA, None)  # o órgão pagando a si mesmo: folha
        elif cnpj_valido(documento.zfill(14)):
            fornecedor = (nome, documento.zfill(14))
        elif e_folha_sem_cnpj(nome):
            fornecedor = (sp.FOLHA, None)
        else:
            fornecedor = (nome, None)
        atual = soma[(ibge, tipo)].setdefault(fornecedor, [Decimal(0), 0])
        atual[0] += pago
        atual[1] += 1
    return soma


def ler(payload: bytes | Path) -> tuple[dict, Any]:
    """(cadastro de órgãos, gerador das linhas do CSV de empenhos)."""
    arquivo = zipfile.ZipFile(io.BytesIO(payload) if isinstance(payload, bytes) else payload)
    orgaos = ler_orgaos(arquivo.read(ORGAOS_NO_ZIP))
    nome = next(n for n in arquivo.namelist() if n.endswith(".csv") and n != ORGAOS_NO_ZIP)

    def linhas() -> Any:
        with arquivo, arquivo.open(nome) as bruto:
            texto = io.TextIOWrapper(bruto, encoding="utf-8-sig", newline="")
            yield from csv.DictReader(texto)

    return orgaos, linhas()


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        caminho = comum.baixar_para_arquivo(client, URL.format(ano=ano))
        orgaos = comum.get_bytes(client, URL_ORGAOS)
        with zipfile.ZipFile(caminho, "a") as arquivo:  # o cadastro vai junto no bruto
            info = zipfile.ZipInfo(ORGAOS_NO_ZIP, (1980, 1, 1, 0, 0, 0))  # data fixa: sha estável
            info.compress_type = zipfile.ZIP_DEFLATED
            arquivo.writestr(info, orgaos)
        return caminho

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        validos = set(session.scalars(select(Municipio.ibge).where(Municipio.uf == "RS")))
        orgaos, linhas = ler(payload)
        fora: Counter = Counter()
        soma = agregar(linhas, ano, orgaos, fora)
        for motivo, total in fora.items():
            print(f"  fora: {motivo}: R$ {total:,.2f}", flush=True)
        linhas_gravar = sp.linhas_para_gravar(soma, ano, validos, fonte=FONTE)
        if len({x["municipio_ibge"] for x in linhas_gravar}) < len(validos) // 2:
            raise ValueError(f"Poucos municípios com despesas em {ano}; abortando.")
        session.execute(
            delete(DespesaFornecedor).where(
                DespesaFornecedor.fonte == FONTE, DespesaFornecedor.ano == ano
            )
        )
        for inicio in range(0, len(linhas_gravar), 5000):
            session.execute(insert(DespesaFornecedor), linhas_gravar[inicio : inicio + 5000])
        return len(linhas_gravar)

    return comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(sonda=URL.format(ano=ano)),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument(
        "--ano", type=int, nargs="*", help="Padrão: os dois últimos anos publicados"
    )
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano or [a - 1 for a in comum.anos_padrao()]:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} linhas", flush=True)
