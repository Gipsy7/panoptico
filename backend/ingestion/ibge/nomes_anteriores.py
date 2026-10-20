"""Nomes anteriores de municípios (alterações toponímicas do IBGE), para casar nomes antigos.

Fonte oficial: planilhas anuais de `alteracoes_toponimicas_municipais` no geoftp do IBGE
(uma por ano, 2014 a 2024). Cada linha traz o código do município (UF + 5 dígitos), o nome
anterior, o nome atual, a justificativa (lei ou correção ortográfica) e a data.

Este módulo GERA `data/municipios_nomes_anteriores.csv` (versionado, revisável linha a linha) e
o LÊ para o casamento de nomes. Não há semelhança de texto aqui: só o que o IBGE registrou, mais
as linhas manuais de `data/municipios_nomes_extra.csv` (cada uma com o link oficial da prova).

Para regenerar (precisa de xlrd, só para ler .xls antigo):
    python -m uv run --with xlrd python -m ingestion.ibge.nomes_anteriores --gerar
"""

import argparse
import csv
import re
from functools import lru_cache
from pathlib import Path

from ingestion import comum

BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/"
    "alteracoes_toponimicas_municipais/"
)
ANOS = (2014, 2024)  # a de 2014 traz o histórico antigo; a de 2024, de 2017 em diante
RAIZ = Path(__file__).resolve().parents[3] / "data"
CSV_IBGE = RAIZ / "municipios_nomes_anteriores.csv"
CSV_EXTRA = RAIZ / "municipios_nomes_extra.csv"
COLUNAS = ["uf", "nome_na_fonte", "ibge", "fonte", "data", "justificativa"]
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip


def _data(valor, datemode) -> str:
    import xlrd

    if isinstance(valor, float):
        return xlrd.xldate_as_datetime(valor, datemode).date().isoformat()
    return str(valor or "").strip()


def _linhas_xls(conteudo: bytes) -> list[dict]:
    """Dois layouts: a planilha de 2014 (histórico até então) e a de 2024 (de 2017 em diante)."""
    import xlrd  # só na geração

    wb = xlrd.open_workbook(file_contents=conteudo)
    folha = wb.sheet_by_index(0)
    cab = [str(c).strip().upper() for c in folha.row_values(0)]
    saida = []
    for i in range(1, folha.nrows):
        linha = dict(zip(cab, folha.row_values(i), strict=False))
        if "UF_MUNIC" in linha:  # 2014
            ibge = str(linha["UF_MUNIC"]).strip()
            anterior, data = linha["NOME ANTERIOR"], _data(linha["DATA NORMA"], wb.datemode)
            justificativa = f"Norma legal {str(linha['NORMA LEGAL']).strip()}"
        else:  # 2024
            ibge = str(linha["UF"]).strip() + str(linha["MUN"]).strip().zfill(5)
            anterior = linha["NOME_ANTERIOR"]
            data = _data(linha["DATA_OCORRÊNCIA"], wb.datemode)
            justificativa = str(linha["JUSTIFICATIVA DO EVENTO/ATO"]).strip()
        saida.append(
            {"ibge": ibge, "anterior": str(anterior).strip(), "justificativa": justificativa,
             "data": data}
        )  # fmt: skip
    return saida


def gerar() -> int:
    import httpx

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        atuais = {
            str(m["id"]): m["nome"]
            for m in comum.get_json(
                client, "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
            )
        }
        saida: dict[tuple[str, str], dict] = {}
        for ano in ANOS:
            url = f"{BASE}Alteracoes_Toponimicas_Municipais_{ano}.xls"
            resp = client.get(url)
            resp.raise_for_status()
            for linha in _linhas_xls(resp.content):
                ibge = linha["ibge"]
                uf = UF_POR_CODIGO.get(ibge[:2])
                if ibge not in atuais or uf is None:
                    print(f"  ignorado (código fora do IBGE atual): {ibge} {linha['anterior']}")
                    continue
                if comum.chave_nome(linha["anterior"]) == comum.chave_nome(atuais[ibge]):
                    continue  # só acento/pontuação: o casamento normal já resolve
                saida[(uf, comum.chave_nome(linha["anterior"]))] = {
                    "uf": uf,
                    "nome_na_fonte": linha["anterior"],
                    "ibge": ibge,
                    "fonte": url,
                    "data": linha["data"],
                    "justificativa": linha["justificativa"],
                }
    # Nome anterior que hoje é o nome ATUAL de outro município da mesma UF fica de fora: o
    # casamento exato já o resolve para o município de hoje, e a linha só confundiria.
    atual_por_uf = {(ibge[:2], comum.chave_nome(n)) for ibge, n in atuais.items()}
    linhas = [v for (_, ch), v in saida.items() if (v["ibge"][:2], ch) not in atual_por_uf]
    linhas.sort(key=lambda v: (v["uf"], v["nome_na_fonte"]))
    with CSV_IBGE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    return len(linhas)


@lru_cache(maxsize=1)
def carregar_apelidos() -> dict[tuple[str, str], str]:
    """(UF, chave do nome na fonte) -> IBGE. Mesmo nome para municípios diferentes é descartado."""
    mapa: dict[tuple[str, str], str] = {}
    ambiguos: set[tuple[str, str]] = set()
    for caminho in (CSV_IBGE, CSV_EXTRA):
        if not caminho.exists():
            continue
        with caminho.open(encoding="utf-8", newline="") as f:
            for linha in csv.DictReader(f):
                if not re.fullmatch(r"\d{7}", linha["ibge"]) or not linha["fonte"].startswith(
                    "http"
                ):
                    raise ValueError(f"Linha inválida em {caminho.name}: {linha}")
                chave = (linha["uf"], comum.chave_nome(linha["nome_na_fonte"]))
                if chave in mapa and mapa[chave] != linha["ibge"]:
                    ambiguos.add(chave)
                mapa[chave] = linha["ibge"]
    for chave in ambiguos:
        del mapa[chave]
    return mapa


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nomes anteriores de municípios (IBGE)")
    parser.add_argument("--gerar", action="store_true", help="Baixa as planilhas e grava o CSV")
    args = parser.parse_args()
    if args.gerar:
        print(f"{CSV_IBGE.name}: {gerar()} nomes anteriores")
