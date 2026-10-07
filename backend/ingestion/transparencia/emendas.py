"""Emendas parlamentares (Portal da Transparência, arquivo único em lote).

O arquivo traz todas as emendas desde 2014 (CSV em latin-1, separador `;`). Ficam as
da legislatura atual em diante. O autor vem com um código do sistema de orçamento e o
nome em maiúsculas; ligamos o código ao parlamentar pelo nome mais recente usado com
aquele código, comparando sem acentos e sem pontuação. Só correspondência exata.

Do arquivo por favorecido ficam os valores de emendas individuais recebidos por
prefeituras, fundos municipais e entidades sem fins lucrativos, que é o que chega de
fato a cada cidade. Bancos intermediários (Caixa, BB) e empresas ficam de fora: estão
sediados em uma cidade e executam em outra. O município vem só por nome e UF e é
ligado ao código do IBGE pelo nome, com correspondência aproximada dentro da UF.
"""

import argparse
import csv
import difflib
import io
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models import Emenda, EmendaPagamento, FonteIngestao, Municipio, Parlamentar
from ingestion import comum
from ingestion.proposicoes_comum import INICIO_LEGISLATURA

FONTE = "transparencia_emendas"
URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
ARQUIVO = "EmendasParlamentares.csv"
ARQUIVO_FAVORECIDOS = "EmendasParlamentares_PorFavorecido.csv"
SEM_INFORMACAO = "Sem informação"
GRUPOS = {
    "Município": "prefeitura",
    "Fundo Público da Administração Direta Municipal": "prefeitura",
    "Associação Privada": "entidade",
    "Fundação Privada": "entidade",
}


def _valor(texto: str) -> Decimal:
    return Decimal((texto or "0").replace(".", "").replace(",", ".") or "0")


def _info(texto: str) -> str | None:
    texto = (texto or "").strip()
    return None if not texto or texto == SEM_INFORMACAO else texto


def normalizar(conteudo_zip: bytes, ano_minimo: int) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
        texto = z.read(ARQUIVO).decode("latin-1")
    registros = []
    for linha in csv.DictReader(io.StringIO(texto), delimiter=";"):
        ano = int(linha["Ano da Emenda"])
        if ano < ano_minimo:
            continue
        tipo = linha["Tipo de Emenda"].strip()
        registros.append(
            {
                "codigo": linha["Código da Emenda"].strip(),
                "ano": ano,
                "tipo": tipo,
                "individual": tipo.startswith("Emenda Individual"),
                "autor_codigo": linha["Código do Autor da Emenda"].strip(),
                "autor_nome": linha["Nome do Autor da Emenda"].strip(),
                "localidade": linha["Localidade de aplicação do recurso"].strip(),
                "municipio_ibge": _info(linha["Código Município IBGE"]),
                "uf": _info(linha["UF"]),
                "funcao": _info(linha["Nome Função"]),
                "acao": _info(linha["Nome Ação"]),
                "valor_empenhado": _valor(linha["Valor Empenhado"]),
                # Pago no ano + restos a pagar pagos nos anos seguintes.
                "valor_pago": _valor(linha["Valor Pago"])
                + _valor(linha["Valor Restos A Pagar Pagos"]),
            }
        )
    return registros


def normalizar_pagamentos(conteudo_zip: bytes, ano_minimo: int) -> list[dict[str, Any]]:
    """Lê o arquivo por favorecido em fluxo (são centenas de MB descomprimidos)."""
    registros = []
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z, z.open(ARQUIVO_FAVORECIDOS) as f:
        for linha in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            codigo = linha["Código da Emenda"].strip()
            grupo = GRUPOS.get(linha["Natureza Jurídica"].strip())
            if (
                grupo is None
                or not codigo[:4].isdigit()  # há linhas com "Sem informação"
                or int(codigo[:4]) < ano_minimo
                or not linha["Tipo de Emenda"].startswith("Emenda Individual")
            ):
                continue
            registros.append(
                {
                    "emenda_codigo": codigo,
                    "ano_emenda": int(codigo[:4]),
                    "ano_mes": int(linha["Ano/Mês"]),
                    "autor_codigo": linha["Código do Autor da Emenda"].strip(),
                    "autor_nome": linha["Nome do Autor da Emenda"].strip(),
                    "favorecido": linha["Favorecido"].strip(),
                    "favorecido_codigo": linha["Código do Favorecido"].strip(),
                    "natureza": linha["Natureza Jurídica"].strip(),
                    "grupo": grupo,
                    "uf": linha["UF Favorecido"].strip(),
                    "municipio_nome": linha["Município Favorecido"].strip(),
                    "valor": _valor(linha["Valor Recebido"]),
                }
            )
    return registros


def resolver_municipios(
    pagamentos: list[dict[str, Any]], municipios: list[tuple[str, str, str]]
) -> tuple[list[dict[str, Any]], int]:
    """Troca (UF, nome) pelo código IBGE. Devolve os resolvidos e quantos ficaram de fora."""
    exato = {(uf, chave): ibge for ibge, uf, chave in municipios}
    por_uf: dict[str, dict[str, str]] = {}
    for ibge, uf, chave in municipios:
        por_uf.setdefault(uf, {})[chave] = ibge

    cache: dict[tuple[str, str], str | None] = {}

    def resolver(uf: str, nome: str) -> str | None:
        chave = comum.chave_nome(nome)
        if (uf, chave) not in cache:
            ibge = exato.get((uf, chave))
            if ibge is None:  # grafias antigas: "SANTANA DO LIVRAMENTO", "ITAPAGE"...
                proximos = difflib.get_close_matches(chave, por_uf.get(uf, {}), n=1, cutoff=0.88)
                ibge = por_uf[uf][proximos[0]] if proximos else None
            cache[(uf, chave)] = ibge
        return cache[(uf, chave)]

    resolvidos, fora = [], 0
    for p in pagamentos:
        ibge = resolver(p["uf"], p["municipio_nome"])
        if ibge is None:
            fora += 1
            continue
        resto = {k: v for k, v in p.items() if k not in ("uf", "municipio_nome")}
        resolvidos.append({**resto, "municipio_ibge": ibge})
    return resolvidos, fora


def vincular_autores(
    registros: list[dict[str, Any]], parlamentares: list[tuple[int, str]]
) -> dict[str, int]:
    """Código do autor -> id do parlamentar, pelo nome do ano mais recente daquele código.
    Nomes que batem com mais de um parlamentar ficam sem vínculo."""
    por_nome: dict[str, list[int]] = {}
    for id_, nome in parlamentares:
        por_nome.setdefault(comum.chave_nome(nome), []).append(id_)

    nome_recente: dict[str, tuple[int, str]] = {}
    for r in registros:
        if not r["individual"]:
            continue
        atual = nome_recente.get(r["autor_codigo"])
        if atual is None or r["ano"] > atual[0]:
            nome_recente[r["autor_codigo"]] = (r["ano"], r["autor_nome"])

    vinculos = {}
    for codigo, (_, nome) in nome_recente.items():
        candidatos = por_nome.get(comum.chave_nome(nome), [])
        if len(candidatos) == 1:
            vinculos[codigo] = candidatos[0]
    return vinculos


def carregar(session: Session, conteudo: bytes, ingestao: FonteIngestao) -> int:
    ano_minimo = INICIO_LEGISLATURA.year
    registros = normalizar(conteudo, ano_minimo)
    if not registros:
        raise ValueError("Nenhuma emenda no arquivo; abortando.")
    parlamentares = session.execute(
        select(Parlamentar.id, Parlamentar.nome_parlamentar).where(Parlamentar.em_exercicio)
    ).all()
    vinculos = vincular_autores(registros, [(p.id, p.nome_parlamentar) for p in parlamentares])

    session.execute(delete(Emenda).where(Emenda.ano >= ano_minimo))
    linhas = [
        {
            **r,
            "parlamentar_id": vinculos.get(r["autor_codigo"]) if r["individual"] else None,
            "ingestao_id": ingestao.id,
        }
        for r in registros
    ]
    for inicio in range(0, len(linhas), 5000):
        session.execute(insert(Emenda), linhas[inicio : inicio + 5000])

    municipios = session.execute(select(Municipio.ibge, Municipio.uf, Municipio.nome_chave)).all()
    if not municipios:
        raise ValueError("Tabela de municípios vazia; rode ingestion.ibge.municipios antes.")
    pagamentos, fora = resolver_municipios(
        normalizar_pagamentos(conteudo, ano_minimo), [tuple(m) for m in municipios]
    )
    print(f"  pagamentos sem município identificado: {fora}")
    session.execute(delete(EmendaPagamento).where(EmendaPagamento.ano_emenda >= ano_minimo))
    pagamentos = [
        {**p, "parlamentar_id": vinculos.get(p["autor_codigo"]), "ingestao_id": ingestao.id}
        for p in pagamentos
    ]
    for inicio in range(0, len(pagamentos), 5000):
        session.execute(insert(EmendaPagamento), pagamentos[inicio : inicio + 5000])
    return len(linhas) + len(pagamentos)


def executar(de_raw: Path | None = None) -> int:
    def baixar(client: httpx.Client) -> bytes:
        return comum.get_bytes(client, URL)

    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} registros (emendas + pagamentos)")
