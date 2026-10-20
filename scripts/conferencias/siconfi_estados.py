"""Despesa paga 2024 de SP, SC e AC: leitura direta da DCA (SICONFI) x calculo do conector.

    python siconfi_estados.py <ano> <saida.json>

Leitura independente: a linha-resumo "Despesas (Exceto Intraorcamentarias)" da coluna
"Despesas Pagas" no Anexo I-E, e (conferencia cruzada) a soma das funcoes de governo, que e
o que o conector grava como `despesa_paga`.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request

URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
ESTADOS = {"SP": "35", "SC": "42", "AC": "12"}


def consultar(ente: str, ano: int, anexo: str) -> list[dict]:
    itens, off = [], 0
    while True:
        q = urllib.parse.urlencode({"an_exercicio": ano, "no_anexo": anexo, "id_ente": ente, "offset": off})
        for t in range(4):
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": "panoptico-conferencia/1.0"}),
                    timeout=60,
                ) as r:
                    d = json.load(r)
                break
            except Exception as e:  # noqa: BLE001
                print("  tentativa", t, e)
                time.sleep(3 * (t + 1))
        else:
            raise SystemExit("API do SICONFI indisponivel")
        itens += d.get("items", [])
        if not d.get("hasMore"):
            return itens
        off += len(d.get("items", []))


if __name__ == "__main__":
    ano = int(sys.argv[1])
    saida = {}
    for uf, ente in ESTADOS.items():
        saida[uf] = {
            "I-E": consultar(ente, ano, "DCA-Anexo I-E"),
            "I-C": consultar(ente, ano, "DCA-Anexo I-C"),
        }
        print(uf, {k: len(v) for k, v in saida[uf].items()})
    json.dump(saida, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
