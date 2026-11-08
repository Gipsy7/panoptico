"""PIB dos Municípios do IBGE (SIDRA, tabela 5938): PIB a preços correntes e valor adicionado
bruto por atividade (agropecuária, indústria, serviços, administração pública), por município,
estado e Brasil, de 2002 em diante.

API de agregados v3 (`servicodados.ibge.gov.br/api/v3/agregados/5938`). Pedir todos os anos de
todos os municípios de uma vez dá erro 500 (limite de valores por consulta): vai um ano por
consulta, com as seis variáveis. Valores em mil reais; "..." e "-" são sem dado (em 08/11/2026,
2022 e 2023 só tinham o PIB total, sem as atividades). Conferência: a soma dos municípios fecha
com o Brasil (tolerância de 0,5%, por arredondamento), senão a carga aborta.
"""

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, PibIbge
from ingestion import comum

FONTE = "ibge_pib"
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados/5938"
URL = BASE + "/metadados"
PRIMEIRO_ANO = 2002
VARIAVEIS = {
    "37": "pib",
    "498": "vab_total",
    "513": "vab_agropecuaria",
    "517": "vab_industria",
    "6575": "vab_servicos",
    "525": "vab_administracao",
}
NIVEIS = ("N6", "N3", "N1")
AUSENTE = {"...", "..", "-", "X", ""}


def baixar(client: httpx.Client) -> dict[str, Any]:
    fim = int(comum.get_json(client, URL)["periodicidade"]["fim"])
    variaveis = "|".join(VARIAVEIS)
    recorte: dict[str, Any] = {}
    for ano in range(PRIMEIRO_ANO, fim + 1):
        for nivel in NIVEIS:
            corpo = comum.get_json(
                client,
                f"{BASE}/periodos/{ano}/variaveis/{variaveis}",
                {"localidades": f"{nivel}[all]"},
            )
            # {variável: {código: valor}}: só o que a carga usa.
            recorte[f"{nivel}_{ano}"] = {
                v["id"]: {
                    s["localidade"]["id"]: s["serie"].get(str(ano), "")
                    for s in v["resultados"][0]["series"]
                }
                for v in corpo
            }
    return recorte


def _valor(texto: str) -> Decimal | None:
    texto = (texto or "").strip()
    return None if texto in AUSENTE else Decimal(texto)


def normalizar(recorte: dict[str, Any]) -> list[dict[str, Any]]:
    linhas: dict[tuple[str, int], dict[str, Any]] = {}
    for chave, por_variavel in recorte.items():
        ano = int(chave.rsplit("_", 1)[1])
        for variavel, valores in por_variavel.items():
            coluna = VARIAVEIS.get(variavel)
            if coluna is None:
                continue
            for codigo, texto in valores.items():
                linha = linhas.setdefault(
                    (codigo, ano),
                    {"codigo": codigo, "ano": ano, **dict.fromkeys(VARIAVEIS.values())},
                )
                linha[coluna] = _valor(texto)
    return [r for r in linhas.values() if r["pib"] is not None]


def conferir(linhas: list[dict[str, Any]]) -> None:
    for ano in sorted({r["ano"] for r in linhas}):
        do_ano = [r for r in linhas if r["ano"] == ano]
        brasil = sum(r["pib"] for r in do_ano if r["codigo"] == "1")
        municipios = sum(r["pib"] for r in do_ano if len(r["codigo"]) == 7)
        if not brasil or abs(municipios - brasil) > brasil * Decimal("0.005"):
            raise ValueError(f"PIB {ano} não fecha: Brasil {brasil}, municípios {municipios}.")


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    if len({r["codigo"] for r in linhas if len(r["codigo"]) == 7}) < 5000:
        raise ValueError("PIB com menos de 5 mil municípios; abortando.")
    conferir(linhas)
    session.execute(delete(PibIbge))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(PibIbge), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} linhas (município, estado e Brasil por ano)")
