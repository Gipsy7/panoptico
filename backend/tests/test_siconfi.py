# ruff: noqa: E501  (recortes de linhas reais do SICONFI, mais legíveis numa linha só)
from decimal import Decimal

from app.models import ContasMunicipio, Municipio
from ingestion.siconfi import contas

DESPESAS = [
    {"cod_conta": "TotalDespesas", "conta": "Despesas Exceto Intraorçamentárias", "coluna": "Despesas Pagas", "valor": 999, "populacao": 1000},
    {"cod_conta": "TotalDespesas", "conta": "10 - Saúde", "coluna": "Despesas Pagas", "valor": 60, "populacao": 1000},
    {"cod_conta": "TotalDespesas", "conta": "10.301 - Atenção Básica", "coluna": "Despesas Pagas", "valor": 40, "populacao": 1000},
    {"cod_conta": "TotalDespesas", "conta": "01 - Legislativa", "coluna": "Despesas Pagas", "valor": 10, "populacao": 1000},
    {"cod_conta": "TotalDespesas", "conta": "10 - Saúde", "coluna": "Despesas Empenhadas", "valor": 80, "populacao": 1000},
]  # fmt: skip
RECEITAS = [
    {"cod_conta": "TotalReceitas", "conta": "TOTAL", "coluna": "Receitas Brutas Realizadas", "valor": 120},
    {"cod_conta": "TotalReceitas", "conta": "TOTAL", "coluna": "Deduções - FUNDEB", "valor": 5},
]  # fmt: skip


def test_recortar_so_funcoes_pagas_e_total_pela_soma():
    r = contas.recortar("4202404", RECEITAS, DESPESAS)
    assert r["despesa_por_area"] == {"Saúde": 60.0, "Legislativa": 10.0}
    assert (r["despesa_paga"], r["receita_total"], r["populacao"]) == (70.0, 120, 1000)
    assert contas.recortar("1", [], []) is None


def test_contas_do_municipio(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.add_all(
        [
            ContasMunicipio(municipio_ibge="4202404", ano=2024, populacao=1000,
                            receita_total=Decimal("120"), despesa_paga=Decimal("70"),
                            despesa_por_area={"Saúde": 60.0, "Legislativa": 10.0}),
            ContasMunicipio(municipio_ibge="4202404", ano=2023, populacao=1000,
                            receita_total=Decimal("100"), despesa_paga=Decimal("50"),
                            despesa_por_area={}),
        ]
    )  # fmt: skip
    session.flush()
    corpo = client.get("/municipios/4202404/contas").json()
    assert (corpo["ano"], corpo["camara"], corpo["despesa_por_habitante"]) == (2024, 10.0, 0.07)
    assert corpo["por_area"][0] == {"nome": "Saúde", "valor": 60.0, "percentual": 85.7}
    assert corpo["anterior"]["ano"] == 2023
    assert client.get("/municipios/0000000/contas").status_code == 404
