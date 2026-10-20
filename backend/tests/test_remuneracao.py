"""Subsídio parlamentar vigente (app/services/remuneracao.py), Decreto Legislativo 172/2022."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services import remuneracao

# (data, valor esperado, vigente desde): véspera, primeiro dia e meio de cada vigência.
CASOS = [
    (date(2023, 1, 1), Decimal("39293.32"), date(2023, 1, 1)),
    (date(2023, 3, 31), Decimal("39293.32"), date(2023, 1, 1)),
    (date(2023, 4, 1), Decimal("41650.92"), date(2023, 4, 1)),
    (date(2023, 12, 15), Decimal("41650.92"), date(2023, 4, 1)),
    (date(2024, 1, 31), Decimal("41650.92"), date(2023, 4, 1)),
    (date(2024, 2, 1), Decimal("44008.52"), date(2024, 2, 1)),
    (date(2025, 1, 31), Decimal("44008.52"), date(2024, 2, 1)),
    (date(2025, 2, 1), Decimal("46366.19"), date(2025, 2, 1)),
    (date(2030, 6, 1), Decimal("46366.19"), date(2025, 2, 1)),  # depois da última: mantém
]


@pytest.mark.parametrize(("em", "valor", "desde"), CASOS)
def test_vigente_em_cada_vigencia(em, valor, desde):
    r = remuneracao.vigente(em)
    assert (r["subsidio_mensal"], r["vigente_desde"]) == (valor, desde)
    assert r["fonte_url"] == remuneracao.FONTE_URL
    assert r["fonte_nome"] == remuneracao.FONTE_NOME


def test_vespera_de_cada_vigencia_ainda_e_a_anterior():
    for (inicio, _), (_, valor_anterior) in zip(
        remuneracao.SUBSIDIOS[1:], remuneracao.SUBSIDIOS[:-1], strict=True
    ):
        assert remuneracao.vigente(inicio - timedelta(days=1))["subsidio_mensal"] == valor_anterior


def test_sem_data_usa_hoje():
    assert remuneracao.vigente() == remuneracao.vigente(date.today())


def test_antes_da_primeira_vigencia_nao_ha_valor():
    # A tabela começa em 2023-01-01; antes disso não há subsídio transcrito, e a função
    # falha em vez de inventar um valor. Hoje só é chamada com a data corrente.
    with pytest.raises(ValueError):
        remuneracao.vigente(date(2022, 12, 31))
