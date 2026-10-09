"""Despesas das prefeituras e câmaras de São Paulo, dados abertos do TCE-SP.

Um arquivo por ano com cada empenho, liquidação e pagamento de todos os órgãos municipais
(15 GB descompactado em 2024). É baixado para o disco e lido em fluxo; guardamos só o
total PAGO por fornecedor, por município e órgão (prefeitura, câmara, outros), e só os
maiores fornecedores de cada órgão. Pagamentos a pessoas físicas são somados numa linha
sem nomes (servidores, autônomos, beneficiários: cidadãos comuns).
"""

import argparse
import csv
import io
import re
import zipfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import DespesaFornecedor, FonteIngestao, Municipio
from ingestion import comum

FONTE = "tce_sp"
URL = "https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ano}.zip"
MAIORES = 25
PESSOAS_FISICAS = "Pessoas físicas (nomes não exibidos)"
DEMAIS = "Demais fornecedores"
FOLHA = "Folha de pagamento (salários)"


def tipo_de_orgao(nome: str) -> str:
    nome = nome.upper()
    if "CÂMARA" in nome or "CAMARA" in nome:
        return "camara"
    if "PREFEITURA" in nome:
        return "prefeitura"
    return "outros"


PREFIXOS_ORGAO = re.compile(
    r"^(PREFEITURA MUNICIPAL DE|PREFEITURA DO MUNICIPIO DE|PREFEITURA DE|MUNICIPIO DE|"
    r"CAMARA MUNICIPAL DE|CAMARA DE VEREADORES DE|CAMARA DE) "
)


def e_folha(credor: str, orgao: str) -> bool:
    """O órgão pagando a si mesmo é a folha de salários, não um fornecedor. Visto como
    "CAMARA MUNICIPAL DE CAMPINAS" na câmara de Campinas, "MUNICIPIO DE CAMPINAS" (com o
    CNPJ da prefeitura) na prefeitura, ou um credor "FOLHA DE PAGAMENTO". O instituto de
    previdência ("... DO MUNICIPIO DE CAMPINAS") não é o órgão e continua como fornecedor."""
    credor, orgao = comum.chave_nome(credor), comum.chave_nome(orgao)
    if "FOLHA" in credor:
        return True
    if len(credor) > 10 and (credor in orgao or orgao in credor):
        return True
    nucleo_credor = PREFIXOS_ORGAO.sub("", credor)
    return nucleo_credor != credor and nucleo_credor == PREFIXOS_ORGAO.sub("", orgao)


def valor(texto: str) -> Decimal:
    try:
        return Decimal((texto or "0").strip().replace(".", "").replace(",", "."))
    except ArithmeticError:
        return Decimal(0)


def agregar(linhas: Any) -> dict[tuple[str, str], dict[tuple[str, str | None], list]]:
    """(ibge, órgão) -> {(fornecedor, CNPJ): [valor pago, nº de pagamentos]}."""
    soma: dict[tuple[str, str], dict[tuple[str, str | None], list]] = defaultdict(dict)
    for linha in linhas:
        if linha.get("tp_despesa") != "Valor Pago":
            continue
        chave = (linha["codigo_municipio_ibge"].strip(), tipo_de_orgao(linha["ds_orgao"]))
        if "FÍSICA" in (linha.get("tp_identificador_despesa") or "").upper():
            fornecedor = (PESSOAS_FISICAS, None)
        elif e_folha(linha.get("ds_despesa") or "", linha["ds_orgao"]):
            fornecedor = (FOLHA, None)
        else:
            documento = "".join(
                c for c in linha.get("nr_identificador_despesa") or "" if c.isdigit()
            )
            fornecedor = (
                " ".join((linha.get("ds_despesa") or "Não identificado").split())[:300],
                documento[:20] or None,
            )
        atual = soma[chave].setdefault(fornecedor, [Decimal(0), 0])
        atual[0] += valor(linha.get("vl_despesa"))
        atual[1] += 1
    return soma


def linhas_para_gravar(soma: dict, ano: int, validos: set[str], fonte: str = FONTE) -> list[dict]:
    """Os MAIORES fornecedores de cada órgão; o resto vira "Demais fornecedores" e as
    pessoas físicas uma linha sem nomes. Usado também pelos outros TCEs."""
    resultado = []
    for (ibge, orgao), fornecedores in soma.items():
        if ibge not in validos:
            continue
        pessoas = fornecedores.pop((PESSOAS_FISICAS, None), None)
        ordenados = sorted(fornecedores.items(), key=lambda item: item[1][0], reverse=True)
        principais, resto = ordenados[:MAIORES], ordenados[MAIORES:]
        base = {"municipio_ibge": ibge, "ano": ano, "orgao": orgao, "fonte": fonte}
        for (nome, documento), (total, quantos) in principais:
            resultado.append(
                {
                    **base,
                    "fornecedor": nome,
                    "documento": documento,
                    "valor_pago": total,
                    "pagamentos": quantos,
                }
            )
        if resto:
            resultado.append(
                {**base, "fornecedor": DEMAIS, "documento": None,
                 "valor_pago": sum((v[0] for _, v in resto), Decimal(0)),
                 "pagamentos": sum(v[1] for _, v in resto)}
            )  # fmt: skip
        if pessoas:
            resultado.append(
                {
                    **base,
                    "fornecedor": PESSOAS_FISICAS,
                    "documento": None,
                    "valor_pago": pessoas[0],
                    "pagamentos": pessoas[1],
                }
            )
    return resultado


def ler(payload: bytes | Path) -> Any:
    with zipfile.ZipFile(io.BytesIO(payload) if isinstance(payload, bytes) else payload) as z:
        nome = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(nome) as bruto:
            yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="latin-1"), delimiter=";")


def executar(ano: int, de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> Path:
        return comum.baixar_para_arquivo(client, URL.format(ano=ano))

    def carregar(session: Session, payload: Any, ingestao: FonteIngestao) -> int:
        validos = set(session.scalars(select(Municipio.ibge).where(Municipio.uf == "SP")))
        linhas = linhas_para_gravar(agregar(ler(payload)), ano, validos)
        if len({x["municipio_ibge"] for x in linhas}) < len(validos) // 2:
            raise ValueError(f"Poucos municípios com despesas em {ano}; abortando.")
        session.execute(
            delete(DespesaFornecedor).where(
                DespesaFornecedor.fonte == FONTE, DespesaFornecedor.ano == ano
            )
        )
        for inicio in range(0, len(linhas), 5000):
            session.execute(insert(DespesaFornecedor), linhas[inicio : inicio + 5000])
        return len(linhas)

    resultado = comum.executar_ingestao(
        FONTE,
        URL.format(ano=ano),
        baixar,
        carregar,
        de_raw=de_raw,
        prefixo_raw=f"{ano}_",
        incremental=comum.Incremental(sonda=URL.format(ano=ano)),
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument(
        "--ano", type=int, nargs="*", help="Padrão: os dois últimos anos publicados"
    )
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto (um ano só)")
    args = parser.parse_args()
    for ano in args.ano or [a - 1 for a in comum.anos_padrao()]:
        print(f"{FONTE} {ano}: {executar(ano, de_raw=args.de_raw)} linhas", flush=True)
