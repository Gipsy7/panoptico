"""PPM do IBGE: subconjuntos fora, conferência dos bovinos (valores reais de Blumenau, 2025)."""

from decimal import Decimal

import pytest

from ingestion.ibge import ppm


def _rec(rebanho: dict, produto: dict) -> dict:
    return {"ano": 2025, "valores": {"rebanho": rebanho, "produto": produto}}


def test_normalizar_tira_subconjuntos_e_zeros():
    rec = _rec(
        {"Bovino": {"4202404": "6824", "1": "6824"},
         "Suíno - matrizes de suínos": {"4202404": "300"},
         "Galináceos - galinhas": {"4202404": "500000"}, "Ovino": {"4202404": "-"}},
        {"Ovos de galinha": {"4202404": "111662"}, "Lã": {"4202404": "..."}},
    )  # fmt: skip
    itens = {(r["categoria"], r["item"]): r["valor"] for r in ppm.normalizar(rec)}
    assert itens == {
        ("rebanho", "Bovino"): Decimal(6824),
        ("produto", "Ovos de galinha"): Decimal(111662),
    }
    ppm.conferir(ppm.normalizar(rec))


def test_conferir_bovinos():
    with pytest.raises(ValueError):
        ppm.conferir(ppm.normalizar(_rec({"Bovino": {"4202404": "10", "1": "100"}}, {})))
