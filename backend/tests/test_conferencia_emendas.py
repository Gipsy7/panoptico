# ruff: noqa: E501
"""Conferência de 20/10/2026 (docs/conferencias/2026-10-20.md) em testes sem rede.

- o arquivo por favorecido fecha: o que entra + o que fica fora = a soma literal;
- BUG 1 (corrigido): municípios que mudaram de nome entram pela tabela oficial do IBGE;
- BUG 2 (corrigido): plano Pix "Impedido" fica fora do previsto e é contado à parte.
"""

from collections import Counter
from decimal import Decimal

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


def test_municipio_com_nome_antigo_na_cgu_entra():
    municipios = [
        ("1400605", "RR", "SAO LUIZ DO ANAUA"),
        ("3515004", "SP", "EMBU DAS ARTES"),
        ("2306306", "CE", "ITAPAJE"),
        ("2401206", "RN", "AREZ"),
        ("5107008", "MT", "POXOREU"),
    ]
    nomes = [("RR", "SÃO LUIZ"), ("SP", "EMBU"), ("CE", "ITAPAGÉ"), ("RN", "ARÊS"),
             ("MT", "POXORÉO")]  # fmt: skip
    pagamentos = [{"uf": uf, "municipio_nome": n, "valor": Decimal(1)} for uf, n in nomes]
    resolvidos, fora = emendas.resolver_municipios(pagamentos, municipios)
    assert fora == 0
    assert {p["municipio_ibge"] for p in resolvidos} == {m[0] for m in municipios}


def test_linha_sem_municipio_e_contada_com_valor():
    pagamentos = [
        {"uf": "SP", "municipio_nome": "LUGAR QUE NAO EXISTE", "valor": Decimal("10.50")},
        {"uf": "SP", "municipio_nome": "LUGAR QUE NAO EXISTE", "valor": Decimal("4.50")},
    ]
    descartes: Counter = Counter()
    resolvidos, fora = emendas.resolver_municipios(
        pagamentos, [("3515004", "SP", "EMBU DAS ARTES")], descartes
    )
    assert resolvidos == [] and fora == 2
    texto = emendas.resumir_sem_municipio(descartes)
    assert "2 linhas, R$ 15.00" in texto and "SP/LUGAR QUE NAO EXISTE (2" in texto


def test_nome_anterior_nao_vale_por_semelhanca():
    """Só entra o nome registrado pelo IBGE; 'Embuu' (parecido, mas fora da tabela) fica de fora
    quando não passa do corte de semelhança já existente."""
    pagamentos = [{"uf": "SP", "municipio_nome": "EMB", "valor": Decimal(1)}]
    _, fora = emendas.resolver_municipios(pagamentos, [("3515004", "SP", "EMBU DAS ARTES")])
    assert fora == 1


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
    assert r["planos"] == 1 and r["valor_planos"] == Decimal("995000")
    assert r["impedidos"]["planos"] == 1
    assert r["impedidos"]["valor"] == Decimal("5970000")
    assert r["impedidos"]["motivos"][0]["situacao"] == "Impedido"
    assert r["planos_sem_pagamento"] == 0
