"""Para cada plano Pix da API: ha pagamento (CGU) com o mesmo codigo de emenda e CNPJ?

    DATABASE_URL=... python planos_x_pagamentos.py <planos.json> <cnpj>
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal as D

from sqlalchemy import create_engine, text

cnpj = sys.argv[2]
planos = json.load(open(sys.argv[1], encoding="utf-8"))[cnpj]
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    pg = {}
    for r in c.execute(
        text("select emenda_codigo, tipo, sum(valor), count(*) from emenda_pagamento where favorecido_codigo=:c group by 1,2"),
        {"c": cnpj},
    ):
        pg.setdefault(r[0], []).append((r[1], r[2], r[3]))
    tr = {
        r[0]: r[1:]
        for r in c.execute(
            text("select emenda_codigo, situacao, valor_total, municipio_ibge from emenda_transferencia where tipo='especial' and beneficiario_cnpj=:c"),
            {"c": cnpj},
        )
    }
tot_plano = tot_pago = D(0)
for x in planos:
    cod = x["numero_emenda_parlamentar_plano_acao"]
    v = D(str(x["valor_custeio_plano_acao"] or 0)) + D(str(x["valor_investimento_plano_acao"] or 0))
    print(cod, x["situacao_plano_acao"], v, "| pagamentos CGU:", pg.get(cod), "| no banco:", tr.get(cod))
print("planos no banco:", len(tr), "da API:", len(planos))
