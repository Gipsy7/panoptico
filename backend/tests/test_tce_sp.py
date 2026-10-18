# ruff: noqa: E501  (recortes de linhas reais do TCE-SP)
from decimal import Decimal

from app.models import DespesaFornecedor, Municipio
from ingestion.tce import sp

BASE = {"codigo_municipio_ibge": "3504602", "tp_identificador_despesa": "CNPJ - PESSOA JURÍDICA"}
LINHAS = [
    {**BASE, "ds_orgao": "CÂMARA MUNICIPAL DE BADY BASSITT", "tp_despesa": "Valor Pago", "nr_identificador_despesa": "05615940000109", "ds_despesa": "BMS CONSTRUCOES", "vl_despesa": "232745,91"},
    {**BASE, "ds_orgao": "CÂMARA MUNICIPAL DE BADY BASSITT", "tp_despesa": "Valor Pago", "nr_identificador_despesa": "05615940000109", "ds_despesa": "BMS CONSTRUCOES", "vl_despesa": "100,09"},
    {**BASE, "ds_orgao": "CÂMARA MUNICIPAL DE BADY BASSITT", "tp_despesa": "Empenhado", "nr_identificador_despesa": "05615940000109", "ds_despesa": "BMS CONSTRUCOES", "vl_despesa": "999999,00"},
    {**BASE, "ds_orgao": "PREFEITURA MUNICIPAL DE BADY BASSITT", "tp_despesa": "Valor Pago", "tp_identificador_despesa": "PESSOA FÍSICA", "nr_identificador_despesa": "12345678900", "ds_despesa": "FULANO DE TAL", "vl_despesa": "50,00"},
]  # fmt: skip


def test_agrega_so_o_pago_e_esconde_pessoas_fisicas():
    soma = sp.agregar(LINHAS)
    camara = soma[("3504602", "camara")]
    assert camara[("BMS CONSTRUCOES", "05615940000109")] == [Decimal("232846.00"), 2]
    prefeitura = soma[("3504602", "prefeitura")]
    assert list(prefeitura) == [(sp.PESSOAS_FISICAS, None)]
    linhas = sp.linhas_para_gravar(soma, 2024, {"3504602"})
    assert {x["fornecedor"] for x in linhas} == {"BMS CONSTRUCOES", sp.PESSOAS_FISICAS}
    assert not any("FULANO" in x["fornecedor"] for x in linhas)
    assert sp.linhas_para_gravar(soma, 2024, set()) == []


def test_folha_de_pagamento_nao_e_fornecedor():
    assert sp.e_folha("CAMARA MUNICIPAL DE CAMPINAS", "CÂMARA MUNICIPAL DE CAMPINAS")
    assert sp.e_folha("CAMARA MUNICIPAL - FOLHA DE PAGAMENTO", "CÂMARA MUNICIPAL DE BADY BASSITT")
    assert not sp.e_folha("BMS CONSTRUCOES", "CÂMARA MUNICIPAL DE BADY BASSITT")
    # A prefeitura pagando ao "município" (o próprio CNPJ) também é folha; a previdência não.
    assert sp.e_folha("MUNICIPIO DE CAMPINAS", "PREFEITURA MUNICIPAL DE CAMPINAS")
    assert not sp.e_folha(
        "INSTITUTO DE PREVIDENCIA SOCIAL DO MUNICIPIO DE CAMPINAS - CAMPREV",
        "PREFEITURA MUNICIPAL DE CAMPINAS",
    )
    assert not sp.e_folha("MUNICIPIO DE VALINHOS", "PREFEITURA MUNICIPAL DE CAMPINAS")


def test_tipo_de_orgao():
    assert sp.tipo_de_orgao("CÂMARA MUNICIPAL DE X") == "camara"
    assert sp.tipo_de_orgao("PREFEITURA MUNICIPAL DE X") == "prefeitura"
    assert sp.tipo_de_orgao("SERVIÇO AUTÔNOMO DE ÁGUA E ESGOTO") == "outros"


def test_fornecedores_do_municipio(client, session):
    session.add(Municipio(ibge="3504602", nome="Bady Bassitt", uf="SP", nome_chave="BADY BASSITT"))
    session.flush()
    for linha in sp.linhas_para_gravar(sp.agregar(LINHAS), 2024, {"3504602"}):
        session.add(DespesaFornecedor(**linha))
    session.flush()
    corpo = client.get("/municipios/3504602/fornecedores").json()
    assert corpo["ano"] == 2024
    camara = next(o for o in corpo["orgaos"] if o["orgao"] == "camara")
    assert camara["total_pago"] == 232846.0
    assert client.get("/municipios/0000000/fornecedores").status_code == 404


def test_nome_de_mei_sai_sem_cpf_na_ingestao_e_na_api(client, session):
    mei = {**BASE, "ds_orgao": "PREFEITURA MUNICIPAL DE BADY BASSITT", "tp_despesa": "Valor Pago", "nr_identificador_despesa": "22066839000165", "ds_despesa": "ELENISE FREIER BEIER 00594280079", "vl_despesa": "10,00"}  # fmt: skip
    linhas = sp.linhas_para_gravar(sp.agregar([mei]), 2024, {"3504602"})
    assert [x["fornecedor"] for x in linhas] == ["ELENISE FREIER BEIER"]
    # Dado antigo, gravado antes da limpeza: a API também limpa na saída.
    session.add(Municipio(ibge="3504602", nome="Bady Bassitt", uf="SP", nome_chave="BADY BASSITT"))
    session.flush()
    session.add(
        DespesaFornecedor(
            **{**linhas[0], "fornecedor": "ELENISE FREIER BEIER 00594280079", "fonte": "tce_sp"}
        )
    )
    session.flush()
    corpo = client.get("/municipios/3504602/fornecedores").json()
    assert corpo["orgaos"][0]["itens"][0]["fornecedor"] == "ELENISE FREIER BEIER"
    assert "00594280079" not in str(corpo)
