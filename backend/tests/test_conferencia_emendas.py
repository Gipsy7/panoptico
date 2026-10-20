# ruff: noqa: E501
"""Conferência de 20/10/2026 (docs/conferencias/2026-10-20.md) em testes sem rede.

- o arquivo por favorecido fecha: o que entra + o que fica fora = a soma literal;
- BUG 1 (xfail): municípios que mudaram de nome ficam de fora (R$ 465 mi no Brasil);
- BUG 2 (xfail): plano Pix "Impedido" é contado como "com pagamento".
"""

from decimal import Decimal

import pytest

from app.models import EmendaTransferencia
from app.services import emendas as servico
from ingestion.transparencia import emendas
from tests.test_emendas import CAB_FAV, _zip

IND = "Emenda Individual - Transferências com Finalidade Definida"


def test_arquivo_por_favorecido_fecha_com_a_soma_literal():
    """Prefeitura/entidade (com e sem código) + o que a carga não guarda = total do arquivo."""
    linhas = [
        f"202512340001;1234;FULANO;0001;{IND};202603;1;PREFEITURA X;Município;PJ;SP;SÃO PAULO;1.000,50",
        f"202512340001;1234;FULANO;0001;{IND};202603;2;CAIXA;Sociedade de Economia Mista;PJ;DF;BRASÍLIA;999,00",
        "Sem informação;S/I;S/I;S/I;Emenda de Relator;201901;3;FUNDO X;Município;PJ;SP;SÃO PAULO;5,00",
        f"202512340002;1234;FULANO;0002;{IND};202604;4;SANTA CASA;Associação Privada;PJ;SP;SÃO PAULO;10,00",
        f"202512340003;1234;FULANO;0003;{IND};202604;5;JOÃO;Sem informação;PF;SP;SÃO PAULO;3,00",
    ]
    conteudo = _zip(**{emendas.ARQUIVO_FAVORECIDOS: "\n".join([CAB_FAV, *linhas])})
    sem_codigo: list[dict] = []
    guardados = emendas.normalizar_pagamentos(conteudo, sem_codigo=sem_codigo)
    entra = sum((p["valor"] for p in guardados), Decimal(0)) + sum(
        (p["valor"] for p in sem_codigo), Decimal(0)
    )
    fora = Decimal("999.00") + Decimal("3.00")  # banco (Economia Mista) e pessoa física
    assert entra + fora == Decimal("1000.50") + Decimal("999.00") + Decimal("5.00") + Decimal(
        "10.00"
    ) + Decimal("3.00")
    assert entra == Decimal("1015.50")


@pytest.mark.xfail(
    strict=True,
    reason="BUG conferência 20/10: 12 municípios com grafia/nome antigo na CGU (São Luiz/RR, "
    "Embu/SP, Açu/RN, Itapagé/CE...) não casam com o IBGE: 716 linhas, R$ 465 mi fora.",
)
def test_municipio_com_nome_antigo_na_cgu_entra():
    municipios = [("1400605", "RR", "SAO LUIZ DO ANAU"), ("3515004", "SP", "EMBU DAS ARTES")]
    pagamentos = [
        {"uf": "RR", "municipio_nome": "SÃO LUIZ", "valor": Decimal(1)},
        {"uf": "SP", "municipio_nome": "EMBU", "valor": Decimal(2)},
    ]
    resolvidos, fora = emendas.resolver_municipios(pagamentos, municipios)
    assert fora == 0 and {p["municipio_ibge"] for p in resolvidos} == {"1400605", "3515004"}


@pytest.mark.xfail(
    strict=True,
    reason="BUG conferência 20/10: plano Pix 'Impedido' entra em planos_com_pagamento quando "
    "outro plano da mesma emenda e CNPJ foi pago (Sobral: 11 planos/R$ 11,39 mi, pago R$ 5,42 mi).",
)
def test_plano_impedido_nao_conta_como_pago(session):
    base = {"tipo": "especial", "emenda_codigo": "202637330001", "ano_emenda": 2026,
            "beneficiario_cnpj": "07598634000137", "municipio_ibge": "2312908"}  # fmt: skip
    session.add_all(
        [
            EmendaTransferencia(
                identificador="A", situacao="Impedido", valor_total=Decimal("5970000"), **base
            ),
            EmendaTransferencia(
                identificador="B", situacao="Ciente", valor_total=Decimal("995000"), **base
            ),
        ]
    )
    session.flush()
    r = servico._previsto(session, "2312908", {("202637330001", "07598634000137")})
    assert r["valor_planos_com_pagamento"] == Decimal("995000")
