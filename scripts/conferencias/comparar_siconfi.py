"""DCA do SICONFI (siconfi_estados.py) x calculo do conector (`recortar`) x tabela do banco.

    DATABASE_URL=... python comparar_siconfi.py <siconfi.json> <ano>
(rodar de dentro de backend/ com `uv run`, para importar o conector)
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal as D

from sqlalchemy import create_engine, text

from ingestion.siconfi.contas import recortar

dados = json.load(open(sys.argv[1], encoding="utf-8"))
ano = int(sys.argv[2])
CODIGO = {"SP": "35", "SC": "42", "AC": "12"}
with create_engine(os.environ["DATABASE_URL"]).connect() as c:
    for uf, v in dados.items():
        pagas = [x for x in v["I-E"] if x["coluna"] == "Despesas Pagas"]
        resumo = next(x for x in pagas if x["conta"].startswith("Despesas Exceto Intra"))
        indep = D(str(resumo["valor"]))
        rec = recortar(CODIGO[uf], v["I-C"], v["I-E"])
        calc = D(str(rec["despesa_paga"]))
        banco = c.execute(
            text("select despesa_paga from contas_estado where uf=:u and ano=:a"), {"u": uf, "a": ano}
        ).scalar()
        print(uf, ano, "linha-resumo DCA:", indep, "| soma das funcoes (conector):", calc,
              "| dif:", indep - calc, "| banco:", banco)
        print("   receita (conector)", rec["receita_total"], "populacao", rec["populacao"])
