"""Pesquisa da Pecuária Municipal (PPM) do IBGE, no último ano publicado, por município, estado
e Brasil:

- tabela 3939, variável 105: efetivo dos rebanhos (cabeças) por tipo;
- tabela 74, variável 215: valor da produção de origem animal (mil reais) por produto (leite,
  ovos, mel...).

Mesma API de agregados v3 da PAM, um estado por consulta. "Suíno - matrizes de suínos" e
"Galináceos - galinhas" são parte de outros totais e ficam de fora, para não contar duas vezes.
A PPM não mede carne nem abate: só rebanhos e produtos de origem animal. "-" é zero (não
guardado), "..." é sem dado.
"""

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import AgroPecuaria, FonteIngestao
from ingestion import comum
from ingestion.ibge.pam import CODIGOS_UF

FONTE = "ibge_ppm"
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
URL = BASE + "/3939/metadados"
# (tabela, variável, classificação, categoria guardada)
CONSULTAS = [("3939", "105", "79", "rebanho"), ("74", "215", "80", "produto")]
SUBCONJUNTOS = {"Suíno - matrizes de suínos", "Galináceos - galinhas"}
AUSENTE = {"...", "..", "X", "", "-"}


def baixar(client: httpx.Client) -> dict[str, Any]:
    ano = int(comum.get_json(client, URL)["periodicidade"]["fim"])
    recorte: dict[str, Any] = {"ano": ano, "valores": {"rebanho": {}, "produto": {}}}
    locais = [f"N6[N3[{uf}]]" for uf in CODIGOS_UF] + ["N3[all]", "N1[all]"]
    for tabela, variavel, classificacao, categoria in CONSULTAS:
        for localidades in locais:
            corpo = comum.get_json(
                client,
                f"{BASE}/{tabela}/periodos/{ano}/variaveis/{variavel}",
                {"localidades": localidades, "classificacao": f"{classificacao}[all]"},
            )
            for item in corpo[0]["resultados"]:
                nome = next(iter(item["classificacoes"][0]["categoria"].values()))
                por_local = recorte["valores"][categoria].setdefault(nome, {})
                for s in item["series"]:
                    por_local[s["localidade"]["id"]] = s["serie"].get(str(ano), "")
    return recorte


def normalizar(recorte: dict[str, Any]) -> list[dict[str, Any]]:
    ano = int(recorte["ano"])
    linhas = []
    for categoria, itens in recorte["valores"].items():
        for item, por_local in itens.items():
            if item in SUBCONJUNTOS:
                continue
            for codigo, texto in por_local.items():
                texto = (texto or "").strip()
                if texto in AUSENTE:
                    continue
                valor = Decimal(texto)
                if valor:
                    linhas.append({"codigo": codigo, "ano": ano, "categoria": categoria,
                                   "item": item, "valor": valor})  # fmt: skip
    return linhas


def conferir(linhas: list[dict[str, Any]]) -> None:
    """O rebanho bovino dos municípios fecha com o do Brasil (0,5%)."""
    bovino = [r for r in linhas if r["categoria"] == "rebanho" and r["item"] == "Bovino"]
    brasil = sum(r["valor"] for r in bovino if r["codigo"] == "1")
    municipios = sum(r["valor"] for r in bovino if len(r["codigo"]) == 7)
    if not brasil or abs(municipios - brasil) > brasil * Decimal("0.005"):
        raise ValueError(f"PPM não fecha: bovinos no Brasil {brasil}, nos municípios {municipios}.")


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    if len({r["codigo"] for r in linhas if len(r["codigo"]) == 7}) < 4000:
        raise ValueError("PPM com menos de 4 mil municípios; abortando.")
    conferir(linhas)
    session.execute(delete(AgroPecuaria))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(AgroPecuaria), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} valores (rebanhos e produtos de origem animal)")
