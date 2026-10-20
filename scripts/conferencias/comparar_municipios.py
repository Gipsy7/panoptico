"""Compara os agregados do CSV (agregar_emendas_csv.py) com a resposta da API por município.

    python comparar_municipios.py <agg.json> <pasta com m<ibge>.json>
"""

from __future__ import annotations

import json
import sys
import unicodedata
from decimal import Decimal as D
from pathlib import Path


def ch(t: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper().split())


def main(agg: str, pasta: str) -> None:
    a = json.load(open(agg, encoding="utf-8"))
    for i, m in a["municipios"].items():
        d = json.load(open(Path(pasta) / f"m{i}.json", encoding="utf-8"))
        print("==", i, d["municipio"]["nome"])
        print(" total_geral csv", m["total"][1], "api", d["total_geral"], "n", m["total"][0])
        for t in d["tipos"]:
            c = m.get("tipo|" + t["tipo"], [0, "0"])
            ok = D(c[1]) == D(str(t["total"])) and c[0] == t["pagamentos"]
            print("  ", t["tipo"], "api", t["total"], t["pagamentos"], "csv", c, "OK" if ok else "DIF")
        sc = m.get("semcodigo", [0, "0"])
        print("  sem_codigo csv", sc, "api", d["sem_identificacao"]["total"], d["sem_identificacao"]["pagamentos"])
        ind = D(m.get("comcodigo|individual", [0, "0"])[1]) + D(m.get("comcodigo|especial", [0, "0"])[1])
        print("  ind+esp com codigo csv", ind, "api total", d["total"])
        aut: dict[str, D] = {}
        for k, (c, s) in m.items():
            if k.startswith("autor|"):
                _, cod, nome, tipo = k.split("|")
                if tipo in ("individual", "especial"):
                    b = ch(nome.split(" (")[0])
                    aut[b] = aut.get(b, D(0)) + D(s)
        print("  top csv (inclui sem codigo)", [(k, str(v)) for k, v in sorted(aut.items(), key=lambda x: -x[1])[:5]])
        api = [(p["parlamentar"]["nome_parlamentar"], p["total"]) for p in d["parlamentares"]] + [
            (o["autor_nome"], o["total"]) for o in d["outros_autores"]
        ]
        print("  top api", sorted(api, key=lambda x: -x[1])[:5])
        csvset = {k for k in aut if k not in ("S/I", "SEM INFORMACAO")}
        print("  n autores csv", len(csvset), "api numero_autores", d["numero_autores"], "outros", d["numero_outros_autores"])
        print("  favorecidos csv", len([k for k in m if k.startswith("favorecido|")]), "api", d["numero_favorecidos"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
