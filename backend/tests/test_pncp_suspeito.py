"""Valor de contrato do PNCP que parece digitado errado: regra, ingestão, pacote e exibição."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    ContasMunicipio,
    Municipio,
    Pessoa,
    PncpAnual,
    PncpContrato,
    PncpDia,
    PncpJanela,
    PncpOrgao,
    PncpSoma,
    PncpSuspeito,
    SocioPessoa,
)
from ingestion.pncp import contratos, pacote, suspeito

CNPJ = "11111111000111"
IBGE = "4202008"


def test_regra_do_valor_suspeito():
    limites = {"1": Decimal("1000")}
    teto = suspeito.TETO_ABSOLUTO
    assert suspeito.limite("M", "1", limites) == Decimal("1000")  # despesa anual do município
    assert suspeito.limite("M", "2", limites) == teto  # município sem contas: só o teto
    assert suspeito.limite("E", "1", limites) == teto  # só órgão municipal usa as contas
    assert suspeito.limite("M", "1", {"1": teto * 2}) == teto  # nunca passa do teto
    assert not suspeito.eh_suspeito(Decimal("1000"), "M", "1", limites)  # igual ao limite vale
    assert suspeito.eh_suspeito(Decimal("1000.01"), "M", "1", limites)
    assert suspeito.eh_suspeito(Decimal("999999999999"), "F", None, None)
    assert not suspeito.eh_suspeito(None, "M", "1", limites)


def test_salto_de_valor_mais_de_100_vezes_o_inicial():
    cem = Decimal("100")
    assert not suspeito.eh_suspeito(Decimal("10000"), "M", "1", None, Decimal("100"))  # 100x vale
    assert suspeito.eh_suspeito(Decimal("10000.01"), "M", "1", None, Decimal("100"))
    assert suspeito.limite("M", "1", None, Decimal("100")) == cem * 100
    for inicial in (None, Decimal(0)):  # sem base de comparação: não dispara
        assert not suspeito.eh_suspeito(Decimal("999999"), "M", "1", None, inicial)
    # vale o menor entre o salto e o limite do município
    assert suspeito.limite("M", "1", {"1": Decimal("500")}, Decimal("100")) == Decimal("500")
    assert suspeito.limite("M", "1", {"1": Decimal("50000")}, Decimal("100")) == Decimal("10000")
    # termo de Campinas: inicial = global no PNCP, então só o caso conhecido o marca
    n = "51885242000140-2-000286/2026"
    v = Decimal("3060318000")
    assert not suspeito.eh_suspeito(v, "M", "3509502", None, v)
    assert suspeito.eh_suspeito(v, "M", "3509502", None, v, n)
    assert not suspeito.eh_suspeito(Decimal("2828730"), "M", "3509502", None, None, n)


def _contas(ano, despesa):
    return ContasMunicipio(
        municipio_ibge=IBGE, ano=ano, despesa_paga=Decimal(despesa), despesa_por_area={}
    )


def test_carregar_limites_usa_o_ano_mais_recente_com_despesa(session):
    session.add(Municipio(ibge=IBGE, nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    session.flush()
    session.add_all([
        _contas(2024, "10"),
        _contas(2025, "20"),
    ])  # fmt: skip
    session.flush()
    assert suspeito.carregar_limites(session)[IBGE] == Decimal("20")


def _contrato_municipal(numero, valor, ibge=IBGE, cnpj=CNPJ):
    return {
        "numeroControlePNCP": numero, "tipoPessoa": "PJ", "niFornecedor": cnpj,
        "nomeRazaoSocialFornecedor": "EMPRESA", "tipoContrato": {"nome": "Contrato"},
        "orgaoEntidade": {"cnpj": "83551549000100", "esferaId": "M", "razaoSocial": "Prefeitura"},
        "unidadeOrgao": {"codigoIbge": ibge, "ufSigla": "SC"},
        "valorGlobal": valor, "dataPublicacaoPncp": "2026-10-01T00:00:00",
    }  # fmt: skip


def test_somar_separa_valor_suspeito_da_soma_municipal_e_marca_o_alvo():
    d = contratos.Dia(date(2026, 10, 1))
    cs = [
        _contrato_municipal("A-1", 400),
        _contrato_municipal("A-2", 600),
        _contrato_municipal("A-3", 999999999999),
    ]
    contratos.somar(d, cs, {CNPJ}, {IBGE: Decimal("1000")})
    assert d.municipais[(IBGE, CNPJ)][:2] == [2, Decimal("1000.00")]
    [s] = d.suspeitos
    assert (s["referencia"], s["valor_global"], s["limite"]) == (
        "A-3", Decimal("999999999999.00"), Decimal("1000"),
    )  # fmt: skip
    # o valor original fica, sem correção, e a marca vai no contrato do alvo
    assert [d.alvo[k]["valor_suspeito"] for k in ("A-1", "A-2", "A-3")] == [False, False, True]
    assert d.alvo["A-3"]["valor_global"] == Decimal("999999999999.00")
    assert sum(v[1] for v in d.somas.values()) == Decimal("1000000000999.00")  # pncp_soma bruta


def test_somar_marca_salto_de_valor_pelo_inicial():
    d = contratos.Dia(date(2026, 10, 1))
    cs = [_contrato_municipal("S-1", 1000), _contrato_municipal("S-2", 1001),
          _contrato_municipal("S-3", 1001)]  # fmt: skip
    cs[0]["valorInicial"], cs[1]["valorInicial"] = 10, 10  # 100x e acima de 100x
    cs[2]["valorInicial"] = 0
    contratos.somar(d, cs, {CNPJ}, None)
    assert [s["referencia"] for s in d.suspeitos] == ["S-2"]
    assert d.suspeitos[0]["limite"] == Decimal("1000")
    assert d.municipais[(IBGE, CNPJ)][:2] == [2, Decimal("2001.00")]
    assert [d.alvo[k]["valor_suspeito"] for k in ("S-1", "S-2", "S-3")] == [False, True, False]


def test_producao_grava_suspeito_e_reler_o_dia_nao_duplica(session):
    d = contratos.Dia(date(2026, 10, 8))
    contratos.somar(
        d, [_contrato_municipal("A-1", 400), _contrato_municipal("A-3", 5000)], set(),
        {IBGE: Decimal("1000")},
    )  # fmt: skip
    for _ in range(2):
        contratos.gravar_dia_producao(session, d)
    [x] = session.scalars(select(PncpSuspeito)).all()
    assert (x.referencia, x.valor_global, x.quantidade) == ("A-3", Decimal("5000.00"), 1)
    assert session.scalar(select(func.sum(PncpJanela.valor_global))) == Decimal("400.00")


# --- pacote -----------------------------------------------------------------------------------

HOJE = date(2026, 10, 10)  # corte da janela: 2026-09-30
CNPJ_A, CNPJ_B = CNPJ, "22222222000122"


def _soma(dia, forn, q, v, tipo="Contrato"):
    return PncpSoma(dia=dia, orgao_cnpj="1" * 14, municipio_ibge=IBGE, tipo_pessoa="PJ",
                    fornecedor_cnpj=forn, tipo_contrato=tipo, quantidade=q,
                    valor_global=Decimal(v))  # fmt: skip


def _dia(dia):
    return PncpDia(dia=dia, total_api=1, lidos=1, receitas=0, empenhos=0, pessoas_fisicas=0,
                   linhas_alvo=0, lido_em=datetime(2026, 10, 9, tzinfo=UTC))  # fmt: skip


@pytest.fixture
def acervo(session):
    session.add(Municipio(ibge=IBGE, nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    session.flush()
    session.add_all([
        PncpOrgao(cnpj="1" * 14, nome="Prefeitura", esfera="M"),
        _contas(2025, "1000"),
        _dia(date(2026, 9, 29)), _dia(date(2026, 10, 9)),
        _soma(date(2026, 9, 29), CNPJ_B, 1, "70"),
        _soma(date(2026, 9, 29), CNPJ_B, 1, "999999999999", "Outros"),  # compactado, absurdo
        _soma(date(2026, 10, 9), CNPJ_A, 1, "1000.01", "Outros"),  # janela, 1 centavo acima
        _soma(date(2026, 10, 9), CNPJ_A, 1, "1000"),  # no limite: vale
        PncpContrato(numero_controle="X-1", orgao_cnpj="1" * 14, esfera="M", municipio_ibge=IBGE,
                     fornecedor_cnpj=CNPJ_A, tipo_contrato="Contrato", receita=False,
                     valor_global=Decimal("5000"), publicado_em=date(2026, 3, 1)),
    ])  # fmt: skip
    session.flush()
    return session


def test_pacote_tira_suspeito_das_somas_e_o_guarda_a_parte(acervo, tmp_path):
    t = pacote.montar(acervo, HOJE)
    assert [
        (x["dia"], x["fornecedor_cnpj"], x["quantidade"], x["valor_global"], x["limite"])
        for x in t["pncp_suspeito"]
    ] == [
        (date(2026, 9, 29), CNPJ_B, 1, Decimal("999999999999.00"), Decimal("1000.00")),
        (date(2026, 10, 9), CNPJ_A, 1, Decimal("1000.01"), Decimal("1000.00")),
    ]  # fmt: skip
    assert [x["valor_global"] for x in t["pncp_anual"]] == [Decimal("70.00")]
    assert [x["valor_global"] for x in t["pncp_janela"]] == [Decimal("1000.00")]
    assert t["pncp_contrato"] == [] or all(
        c["valor_suspeito"] for c in t["pncp_contrato"]
    )  # alvo vazio aqui; a marca é testada abaixo
    # arquivo: o valor original vai inteiro, e carregar duas vezes dá o mesmo resultado
    destino = tmp_path / "p.zip"
    m = pacote.gerar(acervo, destino, HOJE)
    assert m["tabelas"]["pncp_suspeito"]["linhas"] == 2
    manifesto, tabelas = pacote.ler(destino, destino.with_suffix(".manifesto.json"))
    acervo.query(PncpSuspeito).delete()
    for _ in range(2):
        pacote.carregar(acervo, manifesto, tabelas)
    assert acervo.scalar(select(func.count()).select_from(PncpSuspeito)) == 2


def test_pacote_tira_os_saltos_achados_da_api_das_somas(acervo):
    acervo.add(_soma(date(2026, 3, 2), CNPJ_B, 2, "900", "Contrato"))  # 1 salto + 1 normal
    acervo.flush()
    salto = {
        "numero": "1-2-1/2026", "dia": "2026-03-02", "orgao_cnpj": "1" * 14,
        "municipio_ibge": IBGE, "fornecedor_cnpj": CNPJ_B, "tipo_contrato": "Contrato",
        "valor_inicial": "5", "valor_global": "800",
    }  # fmt: skip
    t = pacote.montar(acervo, HOJE, [salto])
    [x] = [x for x in t["pncp_suspeito"] if x["referencia"]]
    assert (x["valor_global"], x["limite"], x["quantidade"]) == (
        Decimal("800"), Decimal("500"), 1,
    )  # fmt: skip
    anual = {(a["fornecedor_cnpj"], a["valor_global"], a["quantidade"]) for a in t["pncp_anual"]}
    assert (CNPJ_B, Decimal("170.00"), 2) in anual  # 70 de 29/09 + 100 que sobrou, sem o salto
    sem = pacote.montar(acervo, HOJE)
    assert not [x for x in sem["pncp_suspeito"] if x["referencia"]]


# --- exibição (API) ---------------------------------------------------------------------------


def _contrato(numero, valor, publicado, suspeito_=False):
    return PncpContrato(
        numero_controle=numero, orgao_cnpj="83551549000100", orgao_nome="Prefeitura",
        uf="SC", municipio_ibge=IBGE, municipio_nome="Exemplo", fornecedor_cnpj=CNPJ,
        fornecedor_nome="EMPRESA LTDA", tipo_contrato="Contrato", receita=False,
        objeto="Merenda", valor_global=Decimal(valor), publicado_em=publicado,
        valor_suspeito=suspeito_,
    )  # fmt: skip


def test_perfil_marca_contrato_suspeito_e_o_tira_do_total(client, session):
    ana = Pessoa(nome="Ana Souza", chave_nome="ANA SOUZA")
    session.add(ana)
    session.flush()
    session.add_all([
        SocioPessoa(pessoa_id=ana.id, cnpj=CNPJ),
        _contrato("83551549000100-2-000001/2026", "1000", date(2026, 3, 1)),
        _contrato("83551549000100-2-000009/2026", "999999999999", date(2026, 7, 1), True),
    ])  # fmt: skip
    session.flush()
    corpo = client.get(f"/pessoas/{ana.id}/contratos").json()
    assert corpo["total_contratos"] == 2 and corpo["valor_total"] == 1000.0
    assert corpo["contratos_suspeitos"] == 1
    # o contrato aparece com o valor original e a marca para o aviso
    assert [(i["valor"], i["valor_suspeito"]) for i in corpo["itens"]] == [
        (999999999999.0, True), (1000.0, False),
    ]  # fmt: skip


def test_cidade_lista_suspeitos_a_parte_do_ranking(client, session):
    session.add(Municipio(ibge=IBGE, nome="Exemplo", uf="SC", nome_chave="EXEMPLO"))
    session.add(PncpAnual(ano=2026, municipio_ibge=IBGE, fornecedor_cnpj="1" * 14,
                          quantidade=1, valor_global=Decimal(500)))  # fmt: skip
    base = {"municipio_ibge": IBGE, "orgao_cnpj": "83551549000100", "limite": Decimal(1000)}
    ref = "83551549000100-2-000003/2026"
    session.add_all([
        PncpSuspeito(dia=date(2026, 5, 1), fornecedor_cnpj="2" * 14, referencia=ref,
                     quantidade=1, valor_global=Decimal("9999999999"), **base),
        PncpSuspeito(dia=date(2025, 5, 1), fornecedor_cnpj="3" * 14, referencia="",
                     quantidade=1, valor_global=Decimal("1"), **base),  # outro ano: fora
    ])  # fmt: skip
    session.flush()
    corpo = client.get(f"/municipios/{IBGE}/fornecedores-pncp").json()
    assert [i["fornecedor_cnpj"] for i in corpo["itens"]] == ["1" * 14]
    assert [(s["fornecedor_cnpj"], s["valor"]) for s in corpo["suspeitos"]] == [
        ("2" * 14, 9999999999.0)
    ]  # fmt: skip
    assert corpo["suspeitos"][0]["url"] == "https://pncp.gov.br/app/contratos/83551549000100/2026/3"
