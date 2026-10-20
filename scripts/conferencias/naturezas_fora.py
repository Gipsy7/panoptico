"""Naturezas juridicas do CSV por favorecido que o site NAO guarda, por valor."""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from collections import defaultdict
from decimal import Decimal as D

GRUPOS = {
    "Município",
    "Fundo Público da Administração Direta Municipal",
    "Associação Privada",
    "Fundação Privada",
}
t = defaultdict(lambda: [0, D(0)])
with zipfile.ZipFile(sys.argv[1]) as z, z.open("EmendasParlamentares_PorFavorecido.csv") as f:
    for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
        nat = r["Natureza Jurídica"].strip()
        if nat in GRUPOS:
            continue
        k = (nat, r["Tipo Favorecido"].strip())
        t[k][0] += 1
        t[k][1] += D((r["Valor Recebido"] or "0").replace(".", "").replace(",", "."))
for (nat, tf), (n, v) in sorted(t.items(), key=lambda x: -x[1][1])[:30]:
    print(f"{v:>18,.2f} {n:7d} {tf[:16]:16s} {nat}")
