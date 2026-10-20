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
    {"cod_conta": "RO1.1.0.0.00.0.0", "conta": "1.1.0.0.00.0.0 - Impostos, Taxas e Contribuições de Melhoria", "coluna": "Receitas Brutas Realizadas", "valor": 30},
    {"cod_conta": "RO1.1.0.0.00.0.0", "conta": "1.1.0.0.00.0.0 - Impostos, Taxas e Contribuições de Melhoria", "coluna": "Outras Deduções da Receita", "valor": 2},
    {"cod_conta": "RO1.7.1.0.00.0.0", "conta": "1.7.1.0.00.0.0 - Transferências da União e de suas Entidades", "coluna": "Receitas Brutas Realizadas", "valor": 50},
    {"cod_conta": "RO2.4.1.0.00.0.0", "conta": "2.4.1.0.00.0.0 - Transferências da União e de suas Entidades", "coluna": "Receitas Brutas Realizadas", "valor": 7.5},
]  # fmt: skip


def test_recortar_so_funcoes_pagas_e_total_pela_soma():
    r = contas.recortar("4202404", RECEITAS, DESPESAS)
    assert r["despesa_por_area"] == {"Saúde": 60.0, "Legislativa": 10.0}
    assert (r["despesa_paga"], r["receita_total"], r["populacao"]) == (70.0, 120, 1000)
    assert contas.recortar("1", [], []) is None


def test_recortar_receita_propria_e_transferencias_da_uniao():
    r = contas.recortar("4202404", RECEITAS, DESPESAS)
    assert (r["receita_propria"], r["transf_uniao"]) == (30, 57.5)
    # Só a conta corrente da União: vale ela; sem nenhuma, fica nulo (nunca zero).
    so_corrente = [x for x in RECEITAS if x["cod_conta"] != "RO2.4.1.0.00.0.0"]
    assert contas.recortar("1", so_corrente, DESPESAS)["transf_uniao"] == 50
    sem_contas = [x for x in RECEITAS if x["cod_conta"] == "TotalReceitas"]
    r = contas.recortar("1", sem_contas, DESPESAS)
    assert (r["receita_propria"], r["transf_uniao"]) == (None, None)


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


def test_contas_media_do_estado_por_habitante(client, session):
    session.add_all(
        [
            Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"),
            Municipio(ibge="4205407", nome="Florianópolis", uf="SC", nome_chave="FLORIANOPOLIS"),
            Municipio(ibge="4200051", nome="Sem população", uf="SC", nome_chave="SEM"),
            Municipio(ibge="4200101", nome="Outro ano", uf="SC", nome_chave="OUTRO"),
            Municipio(ibge="3550308", nome="São Paulo", uf="SP", nome_chave="SAO PAULO"),
        ]
    )
    session.flush()

    def conta(ibge, ano, populacao, despesa):
        return ContasMunicipio(municipio_ibge=ibge, ano=ano, populacao=populacao,
                               receita_total=Decimal("1"), despesa_paga=Decimal(despesa),
                               despesa_por_area={})  # fmt: skip

    session.add_all(
        [
            conta("4202404", 2024, 1000, "100"),  # 0,10 por habitante
            conta("4205407", 2024, 100, "30"),  # 0,30
            conta("4200051", 2024, None, "500"),  # sem população: fora
            conta("4200101", 2023, 10, "999"),  # outro ano: fora
            conta("3550308", 2024, 10, "999"),  # outra UF: fora
        ]
    )
    session.flush()
    corpo = client.get("/municipios/4202404/contas").json()
    assert corpo["despesa_por_habitante"] == 0.1
    assert corpo["media_uf_despesa_por_habitante"] == 0.2  # (0,10 + 0,30) / 2
    assert corpo["municipios_na_media"] == 2
    assert "sem população" in corpo["media_uf_descricao"].lower()


def test_contas_despesa_nula_nao_vira_zero(client, session):
    session.add(Municipio(ibge="3550308", nome="São Paulo", uf="SP", nome_chave="SAO PAULO"))
    session.flush()
    session.add_all(
        [
            ContasMunicipio(municipio_ibge="3550308", ano=2024, populacao=1000,
                            receita_total=Decimal("120"), despesa_paga=None,
                            despesa_por_area={}),
            ContasMunicipio(municipio_ibge="3550308", ano=2023, populacao=1000,
                            receita_total=Decimal("100"), despesa_paga=None,
                            despesa_por_area={}),
        ]
    )  # fmt: skip
    session.flush()
    corpo = client.get("/municipios/3550308/contas").json()
    assert corpo["despesa_paga"] is None
    assert corpo["despesa_por_habitante"] is None
    assert corpo["por_area"] == [] and corpo["camara"] is None
    assert corpo["anterior"]["despesa_paga"] is None


def test_consulta_que_falha_nao_vira_despesa_nula(monkeypatch):
    """Falha da API (None) é refeita; só o que a API entregou vira dado (caso São Paulo 2024)."""
    chamadas = {"I-E": 0}

    def consultar(client, ibge, ano, anexo):
        if anexo == "DCA-Anexo I-C":
            return RECEITAS
        chamadas["I-E"] += 1
        return None if chamadas["I-E"] == 1 else DESPESAS  # 1ª tentativa falha

    monkeypatch.setattr(contas, "_consultar", consultar)
    monkeypatch.setattr(contas.time, "sleep", lambda s: None)
    [r] = contas.baixar(None, 2024, ["3550308"])
    assert chamadas["I-E"] == 2
    assert r["despesa_paga"] == 70.0
