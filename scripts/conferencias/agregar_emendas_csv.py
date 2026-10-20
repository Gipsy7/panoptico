"""Conferência independente das emendas: agrega o CSV por favorecido da CGU.

Não importa nada de `ingestion`: lê o zip da CGU direto e grava um JSON de agregados, que
`conferir_emendas.py` compara com o banco. Uso:

    python agregar_emendas_csv.py <zip da CGU> <saida.json>
"""

from __future__ import annotations

import csv
import io
import json
import sys
import unicodedata
import zipfile
from collections import defaultdict
from decimal import Decimal

ALVOS = {
    ("SC", "GASPAR"): "4205902",
    ("CE", "SOBRAL"): "2312908",
    ("MG", "UBERLANDIA"): "3170206",
    ("AC", "CRUZEIRO DO SUL"): "1200203",
}
GRUPOS = {
    "Município": "prefeitura",
    "Fundo Público da Administração Direta Municipal": "prefeitura",
    "Associação Privada": "entidade",
    "Fundação Privada": "entidade",
}
TIPOS = {
    "Emenda Individual - Transferências com Finalidade Definida": "individual",
    "Emenda Individual - Transferências Especiais": "especial",
    "Emenda de Bancada": "bancada",
    "Emenda de Comissão": "comissao",
    "Emenda de Relator": "relator",
}


def chave(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()
    return " ".join(t.split())


def val(t: str) -> Decimal:
    return Decimal((t or "0").replace(".", "").replace(",", ".") or "0")


def main(zip_path: str, saida: str) -> None:
    nacional = defaultdict(lambda: [0, Decimal(0)])  # (categoria, tipo, ano_pgto, ano_emenda)
    munic = {ibge: defaultdict(lambda: [0, Decimal(0)]) for ibge in ALVOS.values()}
    with zipfile.ZipFile(zip_path) as z, z.open("EmendasParlamentares_PorFavorecido.csv") as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            v = val(r["Valor Recebido"])
            nat = r["Natureza Jurídica"].strip()
            grupo = GRUPOS.get(nat)
            cod = r["Código da Emenda"].strip()
            tipo = TIPOS.get(r["Tipo de Emenda"].strip()) or (
                "individual" if r["Tipo de Emenda"].startswith("Emenda Individual") else "?"
            )
            ap = r["Ano/Mês"][:4]
            ae = cod[:4] if cod[:4].isdigit() else "sem"
            if grupo is None:
                cat = "fora:" + (
                    "banco/estatal"
                    if "Economia Mista" in nat or "Empresa Pública" in nat
                    else "empresa"
                    if "Empres" in nat or "Sociedade" in nat or "Cooperativa" in nat
                    else "pessoa_fisica"
                    if r["Tipo Favorecido"].startswith("Pessoa F")
                    else "outra_natureza"
                )
            else:
                cat = grupo
            nacional[(cat, tipo, ap, ae)][0] += 1
            nacional[(cat, tipo, ap, ae)][1] += v
            if grupo:
                ibge = ALVOS.get((r["UF Favorecido"].strip(), chave(r["Município Favorecido"])))
                if ibge:
                    m = munic[ibge]
                    for k in (
                        ("total",),
                        ("tipo", tipo),
                        ("autor", r["Código do Autor da Emenda"].strip(), r["Nome do Autor da Emenda"].strip(), tipo),
                        ("semcodigo",) if ae == "sem" else ("comcodigo",),
                        ("semcodigo", tipo) if ae == "sem" else ("comcodigo", tipo),
                        ("favorecido", r["Código do Favorecido"].strip(), r["Favorecido"].strip()),
                    ):
                        m["|".join(k)][0] += 1
                        m["|".join(k)][1] += v
    out = {
        "nacional": {"|".join(k): [c, str(s)] for k, (c, s) in nacional.items()},
        "municipios": {
            i: {k: [c, str(s)] for k, (c, s) in m.items()} for i, m in munic.items()
        },
    }
    with open(saida, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("ok", len(nacional), "chaves nacionais")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
