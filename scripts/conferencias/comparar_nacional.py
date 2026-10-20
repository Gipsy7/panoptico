"""Total nacional de emendas pagas: banco do acervo x CSV da CGU (por favorecido).

    DATABASE_URL=... python comparar_nacional.py <agg.json>

Cada linha do CSV cai numa categoria: prefeitura/entidade (as que o site guarda) ou fora:*
(banco/estatal, empresa, pessoa fisica, outra natureza). O que o site guarda e o que sobra
tem de fechar com o total do arquivo; diferenca residual e bug.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from decimal import Decimal as D

from sqlalchemy import create_engine, text

a = json.load(open(sys.argv[1], encoding="utf-8"))
csv_tipo_ano = defaultdict(lambda: [0, D(0)])  # (cat, tipo, ano_pgto)
csv_tipo_anoe = defaultdict(lambda: [0, D(0)])  # (cat, tipo, ano_emenda)
csv_cat = defaultdict(lambda: [0, D(0)])
for k, (c, s) in a["nacional"].items():
    cat, tipo, ap, ae = k.split("|")
    csv_tipo_ano[(cat, tipo, ap)][0] += c
    csv_tipo_ano[(cat, tipo, ap)][1] += D(s)
    csv_tipo_anoe[(cat, tipo, ae)][0] += c
    csv_tipo_anoe[(cat, tipo, ae)][1] += D(s)
    csv_cat[(cat, "sem" if ae == "sem" else "com")][0] += c
    csv_cat[(cat, "sem" if ae == "sem" else "com")][1] += D(s)

e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    db_ano = {
        (r[0], str(r[1])): (r[2], r[3])
        for r in c.execute(text("select tipo, ano_mes/100, count(*), sum(valor) from emenda_pagamento group by 1,2"))
    }
    db_anoe = {
        (r[0], str(r[1])): (r[2], r[3])
        for r in c.execute(text("select tipo, ano_emenda, count(*), sum(valor) from emenda_pagamento group by 1,2"))
    }
    db_sem = {
        (r[0], str(r[1])): (r[2], r[3])
        for r in c.execute(text("select tipo, ano_mes/100, count(*), sum(valor) from emenda_pagamento_sem_codigo group by 1,2"))
    }
    db_nulo = c.execute(
        text("select count(*), coalesce(sum(valor),0) from emenda_pagamento where municipio_ibge is null")
    ).one()
    db_grupo = list(c.execute(text("select grupo, count(*), sum(valor) from emenda_pagamento group by 1")))
    db_sem_grupo = list(c.execute(text("select grupo, count(*), sum(valor) from emenda_pagamento_sem_codigo group by 1")))

print("== Totais por categoria do CSV (todas as linhas)")
for k, (n, s) in sorted(csv_cat.items()):
    print(f"  {k[0]:28s} {k[1]:4s} codigo  n={n:8d}  R$ {s:>20,.2f}")
tot_csv = sum(v[1] for v in csv_cat.values())
print(f"  TOTAL CSV                                    R$ {tot_csv:>20,.2f}")

print("== Banco: emenda_pagamento por grupo", [(g, n, str(s)) for g, n, s in db_grupo])
print("== Banco: sem_codigo por grupo", [(g, n, str(s)) for g, n, s in db_sem_grupo])
print("== Banco: emenda_pagamento sem municipio_ibge", db_nulo)

print("== Por tipo e ANO DO PAGAMENTO: CSV(prefeitura+entidade, com codigo) x banco")
dif_total = D(0)
for t in ("individual", "especial", "bancada", "comissao", "relator"):
    for ano in sorted({k[2] for k in csv_tipo_ano}):
        n = sum(csv_tipo_ano[(g, t, ano)][0] for g in ("prefeitura", "entidade") if (g, t, ano) in csv_tipo_ano)
        s = sum((csv_tipo_ano[(g, t, ano)][1] for g in ("prefeitura", "entidade") if (g, t, ano) in csv_tipo_ano), D(0))
        # exclui as sem codigo (ano_emenda "sem"): estao em outra tabela
        ns = sum(v[0] for (g, tt, ap), v in csv_tipo_ano.items() if False)
        print_ = (t, ano, n, s)
        # com codigo = total - sem codigo
        sem = a_sem = 0
        csv_sem = {}
    # (detalhe por ano mais abaixo)

# Detalhe correto: separa com/sem codigo por (tipo, ano pgto)
cc = defaultdict(lambda: [0, D(0)])
cs = defaultdict(lambda: [0, D(0)])
for k, (n, s) in a["nacional"].items():
    cat, tipo, ap, ae = k.split("|")
    if cat not in ("prefeitura", "entidade"):
        continue
    alvo = cs if ae == "sem" else cc
    alvo[(tipo, ap)][0] += n
    alvo[(tipo, ap)][1] += D(s)
print("tipo        ano    csv_n  csv_valor           banco_n banco_valor         dif_valor")
for t in ("individual", "especial", "bancada", "comissao", "relator"):
    for ano in sorted({k[1] for k in cc}):
        n, s = cc.get((t, ano), (0, D(0)))
        bn, bs = db_ano.get((t, ano), (0, D(0)))
        d = s - D(bs)
        if d != 0 or n != bn:
            print(f"DIF {t:10s} {ano} {n:6d} {s:>18,.2f} {bn:6d} {D(bs):>18,.2f} {d:>14,.2f}")
        dif_total += d
print("dif total (com codigo)", dif_total)
print("SEM CODIGO por (tipo, ano pgto)")
dif2 = D(0)
for (t, ano), (n, s) in sorted(cs.items()):
    bn, bs = db_sem.get((t, ano), (0, D(0)))
    if D(bs) != s or bn != n:
        print(f"DIF {t} {ano} csv {n} {s} banco {bn} {bs}")
    dif2 += s - D(bs)
print("dif total (sem codigo)", dif2)
