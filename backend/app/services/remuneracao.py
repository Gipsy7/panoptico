"""Subsídio dos membros do Congresso Nacional.

É o mesmo para deputados e senadores e é fixado por decreto legislativo, então não há
ingestão: as linhas `subsidio` de `data/custo_mandato_congresso.csv` transcrevem o art. 1º do
Decreto Legislativo nº 172/2022 (o resto da tabela é o custo do mandato, em custo_mandato.py).
A API de remuneração do Portal da Transparência cobre servidores do Executivo, não
parlamentares.
"""

from datetime import date
from decimal import Decimal

from app.services import custo_mandato

FONTE_NOME = "Decreto Legislativo nº 172, de 21 de dezembro de 2022"
FONTE_URL = (
    "https://www2.camara.leg.br/legin/fed/decleg/2022/"
    "decretolegislativo-172-21-dezembro-2022-793529-publicacaooriginal-166604-pl.html"
)

# (vigente a partir de, valor mensal bruto)
SUBSIDIOS: list[tuple[date, Decimal]] = sorted(
    (linha["vigente_desde"], linha["valor_mensal"])
    for linha in custo_mandato.tabela()
    if linha["cargo"] == "deputado_federal" and linha["item"] == "subsidio"
)


def vigente(em: date | None = None) -> dict:
    em = em or date.today()
    desde, valor = max((s for s in SUBSIDIOS if s[0] <= em), key=lambda s: s[0])
    return {
        "subsidio_mensal": valor,
        "vigente_desde": desde,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
    }
