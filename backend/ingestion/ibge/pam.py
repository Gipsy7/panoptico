"""Produção Agrícola Municipal (PAM) do IBGE (SIDRA, tabela 5457): valor da produção das
lavouras temporárias e permanentes, por produto, no último ano publicado, por município, estado
e Brasil.

API de agregados v3. Todos os municípios com todos os 86 produtos numa consulta passa do
limite: vai um estado por consulta (`N6[N3[uf]]`), mais uma para os estados e uma para o
Brasil. Valor em mil reais. "-" é zero (não guardado), "..." é sem dado. Produtos marcados com
"*" no IBGE têm quantidade em outra unidade (mil frutos); a quantidade não é guardada, só o
valor, que é comparável. Conferência: a soma dos municípios fecha com o Brasil (0,5%).
"""

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import AgroLavoura, FonteIngestao
from ingestion import comum

FONTE = "ibge_pam"
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados/5457"
URL = BASE + "/metadados"
VALOR = "215"
CLASSIFICACAO = "782"
# Códigos IBGE das 27 UFs (os mesmos de app/services/pib.py).
CODIGOS_UF = (
    "11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53".split()
)
AUSENTE = {"...", "..", "X", ""}


def baixar(client: httpx.Client) -> dict[str, Any]:
    ano = int(comum.get_json(client, URL)["periodicidade"]["fim"])
    consultas = [f"N6[N3[{uf}]]" for uf in CODIGOS_UF] + ["N3[all]", "N1[all]"]
    recorte: dict[str, Any] = {"ano": ano, "valores": {}}
    for localidades in consultas:
        corpo = comum.get_json(
            client,
            f"{BASE}/periodos/{ano}/variaveis/{VALOR}",
            {"localidades": localidades, "classificacao": f"{CLASSIFICACAO}[all]"},
        )
        for item in corpo[0]["resultados"]:
            produto = next(iter(item["classificacoes"][0]["categoria"].values()))
            por_local = recorte["valores"].setdefault(produto, {})
            for s in item["series"]:
                por_local[s["localidade"]["id"]] = s["serie"].get(str(ano), "")
    return recorte


def normalizar(recorte: dict[str, Any]) -> list[dict[str, Any]]:
    ano = int(recorte["ano"])
    linhas = []
    for produto, por_local in recorte["valores"].items():
        nome = produto.rstrip("*").strip()
        for codigo, texto in por_local.items():
            texto = (texto or "").strip()
            if texto in AUSENTE or texto == "-":
                continue
            valor = Decimal(texto)
            if valor:
                linhas.append({"codigo": codigo, "ano": ano, "produto": nome, "valor": valor})
    return linhas


def conferir(linhas: list[dict[str, Any]]) -> None:
    total = [r for r in linhas if r["produto"] == "Total"]
    brasil = sum(r["valor"] for r in total if r["codigo"] == "1")
    municipios = sum(r["valor"] for r in total if len(r["codigo"]) == 7)
    if not brasil or abs(municipios - brasil) > brasil * Decimal("0.005"):
        raise ValueError(f"PAM não fecha: Brasil {brasil}, municípios {municipios}.")


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    if len({r["codigo"] for r in linhas if len(r["codigo"]) == 7}) < 4000:
        raise ValueError("PAM com menos de 4 mil municípios; abortando.")
    conferir(linhas)
    session.execute(delete(AgroLavoura))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(AgroLavoura), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} valores (produto por lugar)")
