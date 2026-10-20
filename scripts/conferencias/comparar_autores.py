"""Diferença entre os autores da API e os do CSV (por nome normalizado)."""

from __future__ import annotations

import json
import sys
import unicodedata
from decimal import Decimal as D
from pathlib import Path


def ch(t: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper().split())


a = json.load(open(sys.argv[1], encoding="utf-8"))
for i, m in a["municipios"].items():
    d = json.load(open(Path(sys.argv[2]) / f"m{i}.json", encoding="utf-8"))
    csv_ = {}
    for k, (c, s) in m.items():
        if k.startswith("autor|"):
            _, cod, nome, tipo = k.split("|")
            if tipo in ("individual", "especial"):
                csv_[(cod, nome)] = csv_.get((cod, nome), D(0)) + D(s)
    api = {ch(p["parlamentar"]["nome_parlamentar"]): p["total"] for p in d["parlamentares"]}
    api.update({ch(o["autor_nome"].split(" (")[0]): o["total"] for o in d["outros_autores"]})
    cs = {}
    for (cod, nome), v in csv_.items():
        cs[ch(nome.split(" (")[0])] = cs.get(ch(nome.split(" (")[0]), D(0)) + v
    print("==", i, d["municipio"]["nome"], "csv", len(cs), "api", len(api))
    print("  so no csv:", {k: str(v) for k, v in cs.items() if k not in api})
    print("  so na api:", {k: v for k, v in api.items() if k not in cs})
    print("  valores diferentes:", {k: (str(cs[k]), api[k]) for k in api if k in cs and abs(float(cs[k]) - api[k]) > 0.005})
