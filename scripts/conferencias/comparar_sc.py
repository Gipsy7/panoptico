"""Emendas estaduais de SC: CSV do SC Transferencias x tabela emenda_estadual do banco.

    DATABASE_URL=... python comparar_sc.py <emendas.csv>
Independente do conector: le o CSV cru e soma "Valor Repassado" por ano da emenda.
"""

from __future__ import annotations

import csv
import io
import os
import sys
from collections import defaultdict
from decimal import Decimal as D

from sqlalchemy import create_engine, text


def v(t: str | None) -> D:
    t = (t or "").strip().replace("R$", "").strip()
    return D(t.replace(".", "").replace(",", ".")) if t else D(0)


texto = open(sys.argv[1], "rb").read().decode("utf-8-sig")
csv_ano = defaultdict(lambda: [0, D(0), D(0)])
csv_tipo = defaultdict(lambda: [0, D(0)])
props = set()
dup = 0
for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
    ano = x["Ano"]
    a = csv_ano[ano]
    a[0] += 1
    a[1] += v(x["Valor Repassado"])
    tipo = "bancada" if x["Deputado"].strip().upper().startswith("BANCADA") else "individual"
    csv_tipo[(ano, tipo)][0] += 1
    csv_tipo[(ano, tipo)][1] += v(x["Valor Repassado"])
    if x["Nº Proposta"] in props:
        dup += 1
    props.add(x["Nº Proposta"])
print("propostas repetidas no CSV:", dup, "linhas:", sum(a[0] for a in csv_ano.values()))

e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    db = {str(r[0]): (r[1], r[2]) for r in c.execute(text("select ano, count(*), sum(valor_pago) from emenda_estadual where uf='SC' group by 1"))}
    dbt = {(str(r[0]), r[1]): (r[2], r[3]) for r in c.execute(text("select ano, tipo, count(*), sum(valor_pago) from emenda_estadual where uf='SC' group by 1,2"))}
print("ano  csv_n csv_pago        banco_n banco_pago       dif")
for ano in sorted(set(csv_ano) | set(db)):
    n, s, _ = csv_ano.get(ano, (0, D(0), 0))
    bn, bs = db.get(ano, (0, D(0)))
    print(f"{ano} {n:5d} {s:>16,.2f} {bn:5d} {D(bs):>16,.2f} {s - D(bs):>10,.2f} {'OK' if s == D(bs) and n == bn else 'DIF'}")
for k in sorted(set(csv_tipo) | set(dbt)):
    n, s = csv_tipo.get(k, (0, D(0)))
    bn, bs = dbt.get(k, (0, D(0)))
    print("  ", k, n, s, bn, D(bs), "OK" if s == D(bs) and n == bn else "DIF")
