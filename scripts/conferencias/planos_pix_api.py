"""Planos de acao das transferencias especiais (Pix) direto da API do TransfereGov.

    python planos_pix_api.py <saida.json> <cnpj> [<cnpj> ...]
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "https://api.transferegov.gestao.gov.br/transferenciasespeciais/plano_acao_especial"
saida, cnpjs = sys.argv[1], sys.argv[2:]
res = {}
for cnpj in cnpjs:
    linhas, off = [], 0
    while True:
        url = f"{BASE}?cnpj_beneficiario_plano_acao=eq.{cnpj}&limit=1000&offset={off}&order=id_plano_acao"
        req = urllib.request.Request(url, headers={"User-Agent": "panoptico-conferencia/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            pag = json.load(r)
        linhas += pag
        if len(pag) < 1000:
            break
        off += 1000
    res[cnpj] = linhas
    print(cnpj, len(linhas))
json.dump(res, open(saida, "w", encoding="utf-8"), ensure_ascii=False)
