"""Subsídio dos membros do Congresso Nacional.

É o mesmo para deputados e senadores e é fixado por decreto legislativo, então não há
ingestão: a tabela abaixo transcreve o art. 1º do Decreto Legislativo nº 172/2022.
A API de remuneração do Portal da Transparência cobre servidores do Executivo, não
parlamentares.
"""

from datetime import date
from decimal import Decimal

FONTE_NOME = "Decreto Legislativo nº 172, de 21 de dezembro de 2022"
FONTE_URL = (
    "https://www2.camara.leg.br/legin/fed/decleg/2022/"
    "decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html"
)

# (vigente a partir de, valor mensal bruto)
SUBSIDIOS = [
    (date(2023, 1, 1), Decimal("39293.32")),
    (date(2023, 4, 1), Decimal("41650.92")),
    (date(2024, 2, 1), Decimal("44008.52")),
    (date(2025, 2, 1), Decimal("46366.19")),
]


def vigente(em: date | None = None) -> dict:
    em = em or date.today()
    desde, valor = max((s for s in SUBSIDIOS if s[0] <= em), key=lambda s: s[0])
    return {
        "subsidio_mensal": valor,
        "vigente_desde": desde,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
    }
