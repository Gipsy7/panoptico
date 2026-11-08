"""Saneamento por município no Censo 2022 do IBGE (SIDRA), em % dos domicílios particulares
permanentes ocupados (variável 1000381):

- água: tabela 6803, "possui ligação à rede geral e a utiliza como forma principal" (72144);
- esgoto: tabela 6805, "rede geral, rede pluvial ou fossa ligada à rede" (46290);
- lixo: tabela 6892, "coletado" (2520).

O SNIS (agora SINISA) não tem API aberta por município; o Censo traz o mesmo retrato a partir
dos domicílios, com o mesmo método em todo o país. Um ano só (2022): o próximo Censo trará outro.
"""

import argparse
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import FonteIngestao, SaneamentoCenso
from ingestion import comum

FONTE = "ibge_saneamento"
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
URL = BASE + "/6805/metadados"
ANO = 2022
PERCENTUAL = "1000381"
# coluna -> (tabela, classificação, categoria)
INDICADORES = {
    "agua_rede": ("6803", "1821", "72144"),
    "esgoto_rede": ("6805", "11558", "46290"),
    "lixo_coletado": ("6892", "67", "2520"),
}
AUSENTE = {"...", "..", "X", "", "-"}


def baixar(client: httpx.Client) -> dict[str, Any]:
    recorte: dict[str, Any] = {"ano": ANO, "valores": {}}
    for coluna, (tabela, classificacao, categoria) in INDICADORES.items():
        por_local = recorte["valores"].setdefault(coluna, {})
        for nivel in ("N6[all]", "N3[all]", "N1[all]"):
            corpo = comum.get_json(
                client,
                f"{BASE}/{tabela}/periodos/{ANO}/variaveis/{PERCENTUAL}",
                {"localidades": nivel, "classificacao": f"{classificacao}[{categoria}]"},
            )
            for s in corpo[0]["resultados"][0]["series"]:
                por_local[s["localidade"]["id"]] = s["serie"].get(str(ANO), "")
    return recorte


def normalizar(recorte: dict[str, Any]) -> list[dict[str, Any]]:
    linhas: dict[str, dict[str, Any]] = {}
    for coluna, por_local in recorte["valores"].items():
        for codigo, texto in por_local.items():
            texto = (texto or "").strip()
            valor = None if texto in AUSENTE else Decimal(texto)
            linha = linhas.setdefault(
                codigo, {"codigo": codigo, "ano": int(recorte["ano"]), **dict.fromkeys(INDICADORES)}
            )
            linha[coluna] = valor
    return [r for r in linhas.values() if any(r[c] is not None for c in INDICADORES)]


def carregar(session: Session, payload: dict, ingestao: FonteIngestao) -> int:
    linhas = normalizar(payload)
    if len([r for r in linhas if len(r["codigo"]) == 7]) < 5000:
        raise ValueError("Saneamento com menos de 5 mil municípios; abortando.")
    session.execute(delete(SaneamentoCenso))
    lista = [{**r, "ingestao_id": ingestao.id} for r in linhas]
    for inicio in range(0, len(lista), 5000):
        session.execute(insert(SaneamentoCenso), lista[inicio : inicio + 5000])
    return len(lista)


def executar(de_raw: Path | None = None) -> int:
    return comum.executar_ingestao(FONTE, URL, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto sem baixar")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(de_raw=args.de_raw)} lugares (Censo 2022)")
