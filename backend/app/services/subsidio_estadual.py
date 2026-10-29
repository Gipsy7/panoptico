"""Subsídio mensal dos deputados estaduais (e distritais).

Cada Assembleia fixa o valor em lei estadual (art. 27, §2º da Constituição, teto de 75% do
subsídio do deputado federal). Não há ingestão: o valor, o ato e a fonte de cada UF ficam em
`data/salario_deputados_estaduais.csv`, versionado, e só entra número que a própria fonte
oficial publica (nunca 75% calculado). UF sem valor aparece com o motivo.
O valor é o mesmo para todos os deputados da Casa, então não há média para comparar.
"""

import csv
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

CSV = Path(__file__).resolve().parents[3] / "data" / "salario_deputados_estaduais.csv"


@lru_cache(maxsize=1)
def _tabela() -> dict[str, dict]:
    with CSV.open(encoding="utf-8", newline="") as f:
        return {linha["uf"]: linha for linha in csv.DictReader(f)}


def da_uf(uf: str) -> dict | None:
    linha = _tabela().get(uf.upper())
    if linha is None:
        return None
    valor = linha["valor_mensal_bruto"]
    return {
        "valor": float(Decimal(valor)) if valor else None,
        "ato_normativo": linha["ato_normativo"] or None,
        "vigente_desde": date.fromisoformat(linha["vigente_desde"])
        if linha["vigente_desde"]
        else None,
        "fonte_url": linha["fonte_url"] or None,
        "consultado_em": date.fromisoformat(linha["consultado_em"]),
        # Com valor, a observação é só nota de leitura da fonte; sem valor, é o que falta.
        "observacao": linha["observacao"] or None,
    }
