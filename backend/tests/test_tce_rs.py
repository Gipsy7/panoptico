# ruff: noqa: E501  (recortes de linhas reais do TCE-RS)
import csv
import io
import zipfile
from collections import Counter
from decimal import Decimal

from app.models import DespesaFornecedor, Municipio
from ingestion.tce import rs, sp

# Recorte do cadastro de órgãos auditados (orgaos_auditados_rs.csv).
ORGAOS_CSV = """﻿CD_ORGAO,NOME_ORGAO,SIGLA_ORGAO,ESFERA,SETOR_GOVERNAMENTAL,CNPJ,HOME_PAGE,NATUREZA_JURIDICA,CONTABILIDADE,SITUACAO_ORGAO,CD_MUNICIPIO_TCERS,NOME_MUNICIPIO,CD_MUNICIPIO_IBGE
100,AL - ASSEMBLEIA LEGISLATIVA,AL,ESTADUAL,LEGISLATIVO,88243688000181,www.al.rs.gov.br,PUBLICA,4320/64,1-ATIVO,149,PORTO ALEGRE,4314902
40100,PM DE AGUDO,,MUNICIPAL,EXECUTIVO,87531976000179,,PUBLICA,4320/64,1-ATIVO,1,AGUDO,4300109
40101,CM DE AGUDO,,MUNICIPAL,LEGISLATIVO,89250658000165,,PUBLICA,4320/64,1-ATIVO,1,AGUDO,4300109
54900,PM DE PORTO ALEGRE,,MUNICIPAL,EXECUTIVO,92963560000160,,PUBLICA,4320/64,1-ATIVO,149,PORTO ALEGRE,4314902
54907,DMAE - DEP. MUNICIPAL DE ÁGUA E ESGOTOS - PORTO ALEGRE,,MUNICIPAL,AUTARQUIA,92924901000198,,PUBLICA,4320/64,1-ATIVO,149,PORTO ALEGRE,4314902
88434,CONSÓRCIO FAMURS,,MUNICIPAL,CONSÓRCIO ADMINISTRATIVO,30740749000136,,PUBLICA,4320/64,1-ATIVO,149,PORTO ALEGRE,4314902
""".encode()

COLUNAS = (
    "cd_orgao,tipo_operacao,ano_empenho,ano_operacao,nm_credor,tp_pessoa,cnpj_cpf,vl_pagamento"
)
# Linhas reais do arquivo de 2025 (só as colunas usadas); a pessoa física é fictícia.
EMPENHOS_CSV = f"""﻿{COLUNAS}
40100,E,2015,2015,SM SOARES & CIA LTDA,PJ,11804625000122,
40100,P,2015,2015,SM SOARES & CIA LTDA,PJ,11804625000122,2759.79
40100,P,2023,2025,CONPASUL CONSTRUCAO E SERVICOS LTDA,PJ,90063470000197,313215.86
40100,P,2022,2025,CONPASUL CONSTRUCAO E SERVICOS LTDA,PJ,90063470000197,2233.86
40100,P,2022,2025,CONPASUL CONSTRUCAO E SERVICOS LTDA,PJ,90063470000197,-71.28
40100,L,2025,2025,CONPASUL CONSTRUCAO E SERVICOS LTDA,PJ,90063470000197,
40100,P,2025,2025,INATIVOS,PJ,,28704.86
40100,P,2025,2025,SERVIDORES MUNICIPAIS,PJ,,10199.71
40100,P,2025,2025,CAIXA ECONOMICA FEDERAL,PJ,360305129220,192.79
40100,P,2025,2025,FULANO DE TAL,PF,12345678909,150.00
40100,P,2025,2025,BELTRANO DA SILVA,PJ,52998224725,80.00
40101,P,2025,2025,SERVIDORES CAMARA MUNICIPAL,PJ,,718652.94
40101,P,2025,2025,RADIO AGUDO LTDA,PJ,87068292000182,33602.00
54900,P,2025,2025,MUNICIPIO DE PORTO ALEGRE,PJ,92963560000160,1000.00
54907,P,2025,2025,COMPANHIA DE PROCESSAMENTO DE DADOS DO MUNICIPIO DE PORTO AL,PJ,89398473000100,500.00
88434,P,2025,2025,ALGUMA EMPRESA LTDA,PJ,90063470000197,999.00
""".encode()


def _zip() -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as arquivo:
        arquivo.writestr("2025.csv", EMPENHOS_CSV)
        arquivo.writestr(rs.ORGAOS_NO_ZIP, ORGAOS_CSV)
    return saida.getvalue()


def _soma(fora: Counter | None = None) -> dict:
    orgaos, linhas = rs.ler(_zip())
    return rs.agregar(linhas, 2025, orgaos, fora)


def test_cadastro_de_orgaos():
    orgaos = rs.ler_orgaos(ORGAOS_CSV)
    assert "100" not in orgaos  # estadual
    assert orgaos["40100"] == ("4300109", "prefeitura", "87531976000179")
    assert orgaos["40101"][1] == "camara"
    assert orgaos["54907"][1] == "outros"
    assert orgaos["88434"][1] is None  # consórcio fica de fora


def test_so_pagamentos_do_ano_e_folha_separada():
    fora: Counter = Counter()
    soma = _soma(fora)
    prefeitura = soma[("4300109", "prefeitura")]
    # Pagamento de 2015 do histórico de restos a pagar não entra; o estorno negativo entra.
    assert ("SM SOARES & CIA LTDA", "11804625000122") not in prefeitura
    assert prefeitura[("CONPASUL CONSTRUCAO E SERVICOS LTDA", "90063470000197")] == [
        Decimal("315378.44"),
        3,
    ]
    assert prefeitura[(sp.FOLHA, None)] == [Decimal("38904.57"), 2]
    # CNPJ sem os zeros à esquerda.
    assert prefeitura[("CAIXA ECONOMICA FEDERAL", "00360305129220")] == [Decimal("192.79"), 1]
    # Pessoa física e CPF marcado como PJ: somados sem nome.
    assert prefeitura[(sp.PESSOAS_FISICAS, None)] == [Decimal("230.00"), 2]
    assert not any("FULANO" in n or "BELTRANO" in n for n, _ in prefeitura)
    camara = soma[("4300109", "camara")]
    assert set(camara) == {(sp.FOLHA, None), ("RADIO AGUDO LTDA", "87068292000182")}
    # O órgão pagando ao próprio CNPJ é folha; a autarquia é "outros".
    assert list(soma[("4314902", "prefeitura")]) == [(sp.FOLHA, None)]
    assert ("4314902", "outros") in soma
    assert fora == {"consórcio intermunicipal": Decimal("999.00")}


def test_linhas_para_gravar_com_a_fonte_do_rs():
    linhas = sp.linhas_para_gravar(_soma(), 2025, {"4300109"}, fonte=rs.FONTE)
    assert {x["fonte"] for x in linhas} == {"tce_rs"}
    assert {x["municipio_ibge"] for x in linhas} == {"4300109"}
    assert all(x["documento"] is None or len(x["documento"]) == 14 for x in linhas)


def test_documentos():
    assert rs.cnpj_valido("90063470000197")
    assert rs.cnpj_valido("00360305129220")
    assert not rs.cnpj_valido("00000000000000")
    assert rs.cpf_valido("52998224725")
    assert not rs.cnpj_valido("00052998224725")
    assert rs.e_folha_sem_cnpj("F U N C I O N A R I O S")
    assert rs.e_folha_sem_cnpj("FLS PAGAMENTO FUNCIONARIOS")
    assert rs.e_folha_sem_cnpj("VEREADORES 17 LEGISLATURA")
    assert not rs.e_folha_sem_cnpj("PASEP")
    assert not rs.e_folha_sem_cnpj("CORPORACION ANDINA DE FOMENTO")


def test_fornecedores_do_municipio_gaucho(client, session):
    session.add(Municipio(ibge="4300109", nome="Agudo", uf="RS", nome_chave="AGUDO"))
    session.flush()
    for linha in sp.linhas_para_gravar(_soma(), 2025, {"4300109"}, fonte=rs.FONTE):
        session.add(DespesaFornecedor(**linha))
    session.flush()
    corpo = client.get("/municipios/4300109/fornecedores").json()
    assert corpo["ano"] == 2025
    assert "Rio Grande do Sul" in corpo["fonte_nome"]
    camara = next(o for o in corpo["orgaos"] if o["orgao"] == "camara")
    assert camara["total_pago"] == 752254.94


def test_csv_tem_as_colunas_usadas():
    cabecalho = next(csv.reader(io.StringIO(EMPENHOS_CSV.decode("utf-8-sig"))))
    assert {"cd_orgao", "tipo_operacao", "ano_operacao", "vl_pagamento", "cnpj_cpf"} <= set(
        cabecalho
    )
