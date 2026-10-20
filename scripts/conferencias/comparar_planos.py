"""Planos Pix da API do TransfereGov x bloco `previsto` da API do site.

    python comparar_planos.py <planos.json> <pasta com m<ibge>.json>
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

CNPJ_IBGE = {
    "83102244000102": "4205902",
    "07598634000137": "2312908",
    "18431312000115": "3170206",
    "04012548000102": "1200203",
}
p = json.load(open(sys.argv[1], encoding="utf-8"))
for cnpj, linhas in p.items():
    ibge = CNPJ_IBGE[cnpj]
    d = json.load(open(Path(sys.argv[2]) / f"m{ibge}.json", encoding="utf-8"))
    v = sum(D(str(x["valor_custeio_plano_acao"] or 0)) + D(str(x["valor_investimento_plano_acao"] or 0)) for x in linhas)
    pr = d["previsto"]
    esp = next(t for t in d["tipos"] if t["tipo"] == "especial")
    print(ibge, cnpj, "API:", len(linhas), v, "| site:", pr["planos"], pr["valor_planos"], "| "
          "OK" if len(linhas) == pr["planos"] and v == D(str(pr["valor_planos"])) else "DIF")
    print("   situacoes", dict(Counter(x["situacao_plano_acao"] for x in linhas)))
    print("   site: com pagamento", pr["planos_com_pagamento"], pr["valor_planos_com_pagamento"],
          "sem", pr["planos_sem_pagamento"], pr["valor_sem_pagamento"], "| pago especial (CGU)", esp["total"], esp["pagamentos"])
    if "-v" in sys.argv:
        for x in linhas:
            print("    ", x["numero_emenda_parlamentar_plano_acao"], x["situacao_plano_acao"],
                  x["valor_custeio_plano_acao"], x["valor_investimento_plano_acao"])
