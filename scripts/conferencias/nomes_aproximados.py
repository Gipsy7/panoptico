"""Nomes de municipio do CSV que nao casam exato com o IBGE mas entraram (casamento aproximado).

    DATABASE_URL=... python nomes_aproximados.py <zip da CGU>
Mostra, para cada (UF, nome da CGU) aproximado, o municipio do IBGE para onde o site mandou.
"""

from __future__ import annotations

import csv
import io
import os
import re
import sys
import unicodedata
import zipfile
from collections import defaultdict
from decimal import Decimal as D

from sqlalchemy import create_engine, text

GRUPOS = {
    "Município",
    "Fundo Público da Administração Direta Municipal",
    "Associação Privada",
    "Fundação Privada",
}


def ch(t: str) -> str:
    s = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^A-Z ]", " ", s.upper()).split())


e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    exato = {(r[1], ch(r[2])): r[0] for r in c.execute(text("select ibge, uf, nome from municipio"))}
    nome_ibge = {r[0]: (r[1], r[2]) for r in c.execute(text("select ibge, uf, nome from municipio"))}
    # fuzzy: o banco guarda (favorecido_codigo, valor, ano_mes) -> ibge
    db = {}
    for r in c.execute(text("select emenda_codigo, ano_mes, favorecido_codigo, valor, municipio_ibge from emenda_pagamento")):
        db[(r[0], str(r[1]), r[2], D(r[3]))] = r[4]
vistos = defaultdict(lambda: [set(), 0, D(0)])
with zipfile.ZipFile(sys.argv[1]) as z, z.open("EmendasParlamentares_PorFavorecido.csv") as f:
    for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
        if r["Natureza Jurídica"].strip() not in GRUPOS:
            continue
        cod = r["Código da Emenda"].strip()
        if not cod[:4].isdigit():
            continue
        uf, mun = r["UF Favorecido"].strip(), r["Município Favorecido"].strip()
        if (uf, ch(mun)) in exato:
            continue
        v = D((r["Valor Recebido"] or "0").replace(".", "").replace(",", "."))
        ibge = db.get((cod, r["Ano/Mês"], r["Código do Favorecido"].strip(), v))
        if ibge:
            k = (uf, mun)
            vistos[k][0].add(ibge)
            vistos[k][1] += 1
            vistos[k][2] += v
for (uf, mun), (ibges, n, v) in sorted(vistos.items(), key=lambda x: -x[1][2]):
    print(f"{uf} {mun[:30]:30s} -> {[nome_ibge[i] for i in ibges]} n={n} R$ {v:,.2f}")
