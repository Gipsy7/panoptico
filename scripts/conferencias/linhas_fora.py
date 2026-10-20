"""Linhas do CSV (prefeitura/entidade) que nao estao no banco, classificadas por motivo.

    DATABASE_URL=... python linhas_fora.py <zip da CGU>
"""

from __future__ import annotations

import csv
import io
import os
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal as D

from sqlalchemy import create_engine, text

GRUPOS = {
    "Município",
    "Fundo Público da Administração Direta Municipal",
    "Associação Privada",
    "Fundação Privada",
}


def ch(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()
    return " ".join(t.split())


e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    munis = {(r[1], ch(r[2])) for r in c.execute(text("select ibge, uf, nome from municipio"))}
    db = Counter()
    for r in c.execute(text("select emenda_codigo, ano_mes, favorecido_codigo, valor from emenda_pagamento")):
        db[("c", r[0], str(r[1]), r[2], D(r[3]))] += 1
    for r in c.execute(text("select ano_mes, favorecido_codigo, valor, tipo from emenda_pagamento_sem_codigo")):
        db[("s", str(r[0]), r[1], D(r[2]), r[3])] += 1

fora = defaultdict(lambda: [0, D(0)])
exemplos = defaultdict(list)
with zipfile.ZipFile(sys.argv[1]) as z, z.open("EmendasParlamentares_PorFavorecido.csv") as f:
    for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
        if r["Natureza Jurídica"].strip() not in GRUPOS:
            continue
        cod = r["Código da Emenda"].strip()
        v = D((r["Valor Recebido"] or "0").replace(".", "").replace(",", "."))
        tipo = r["Tipo de Emenda"].strip()
        if cod[:4].isdigit():
            k = ("c", cod, r["Ano/Mês"], r["Código do Favorecido"].strip(), v)
        else:
            tp = {
                "Emenda Individual - Transferências com Finalidade Definida": "individual",
                "Emenda Individual - Transferências Especiais": "especial",
                "Emenda de Bancada": "bancada",
                "Emenda de Comissão": "comissao",
                "Emenda de Relator": "relator",
            }.get(tipo)
            k = ("s", r["Ano/Mês"], r["Código do Favorecido"].strip(), v, tp)
        if db[k] > 0:
            db[k] -= 1
            continue
        uf, mun = r["UF Favorecido"].strip(), r["Município Favorecido"].strip()
        if (uf, ch(mun)) in munis:
            motivo = "municipio_existe_mas_linha_ausente"
        elif not uf or ch(mun) in ("", "SEM INFORMACAO"):
            motivo = "uf/municipio sem informacao"
        else:
            motivo = "nome nao casa com o IBGE"
        kk = (k[0], motivo, uf, mun) if motivo != "municipio_existe_mas_linha_ausente" else (k[0], motivo, "", "")
        fora[kk][0] += 1
        fora[kk][1] += v
        if len(exemplos[kk]) < 2:
            exemplos[kk].append((cod, r["Ano/Mês"], r["Favorecido"].strip(), str(v)))

tot_n = sum(v[0] for v in fora.values())
tot_v = sum((v[1] for v in fora.values()), D(0))
print("LINHAS FORA:", tot_n, f"R$ {tot_v:,.2f}")
por_motivo = defaultdict(lambda: [0, D(0)])
for (cod, motivo, uf, mun), (n, v) in fora.items():
    por_motivo[(cod, motivo)][0] += n
    por_motivo[(cod, motivo)][1] += v
for k, (n, v) in sorted(por_motivo.items()):
    print(" ", k, n, f"R$ {v:,.2f}")
print("Maiores (uf, municipio de origem):")
for kk, (n, v) in sorted(fora.items(), key=lambda x: -x[1][1])[:25]:
    print(f"  {kk[0]} {kk[1][:28]:28s} {kk[2]:3s} {kk[3][:35]:35s} n={n:4d} R$ {v:>16,.2f}  ex={exemplos[kk][0]}")
print("sobras no banco (linhas no banco sem par no CSV):", sum(v for v in db.values() if v > 0))
