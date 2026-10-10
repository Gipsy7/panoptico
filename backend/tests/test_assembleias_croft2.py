# ruff: noqa: E501  (recortes das páginas e APIs reais das assembleias)
import json
from datetime import date
from decimal import Decimal

import httpx
import respx

from ingestion.assembleias import alap, alego, alema, alems, alese, alrn, base

# ---------------- ALEMA ----------------
MA_PAGINA = """
<section class="jumbotron jumbotron--assembleia"><div class="jumbotron-image"><img src="https://www.al.ma.leg.br/sitealema/wp-content/uploads/2024/04/parlamentares_topo.png" alt="Deputados"></div></section>
<div class="news-card">
    <div class="news-card-image">
        <img src="https://www.al.ma.leg.br/sitealema/wp-content/uploads/2024/12/Abigail-Cunha.jpg" alt="Abigail Cunha">
    </div>
    <div class="news-card-content">
        <h3 class="news-card-title"><a href="https://www.al.ma.leg.br/sitealema/deputado/abigail-cunha/">Abigail Cunha</a></h3>
        <p class="news-card-chapeu">MDB</p>
    </div>
</div>
<div class="news-card">
    <div class="news-card-image">
        <img src="https://www.al.ma.leg.br/x/Dra-Vivianne.jpg" alt="Dra. Vivianne">
    </div>
    <div class="news-card-content">
        <h3 class="news-card-title"><a href="https://www.al.ma.leg.br/sitealema/deputado/dra-vivianne/">Dra. Vivianne</a></h3>
        <p class="news-card-chapeu">PSD</p>
    </div>
</div>
<h5>Deputados licenciados</h5>
<div class="news-card">
    <div class="news-card-image">
        <img src="https://www.al.ma.leg.br/x/Edson.jpg" alt="Edson Araújo">
    </div>
    <div class="news-card-content">
        <h3 class="news-card-title"><a href="https://www.al.ma.leg.br/sitealema/deputado/edson-araujo/">Edson Araújo</a></h3>
        <p class="news-card-chapeu">PSB</p>
    </div>
</div>
"""
MA_CADASTRO = [
    {"id": 129, "parliamentaryName": "Dra Vivianne", "fullName": "Dra. Viviane"},
    {"id": 130, "parliamentaryName": "Abigail Cunha", "fullName": "Abigail Cunha"},
]
MA_MATERIAS = [
    {
        "id": 101379,
        "matterTypeSigla": "PLO",
        "number": "269",
        "year": "2026",
        "ement": "Eleva a Catedral de Bonfim,  em Grajaú-MA, à condição de Patrimônio.",
        "authorNames": "Abigail Cunha",
        "presentationDate": "2026-10-09",
    },
    {
        "id": 101300,
        "matterTypeSigla": "IND",
        "number": "10",
        "year": "2026",
        "ement": "Indica",
        "authorNames": "Dra Vivianne",
        "presentationDate": "2026-10-01",
    },
    {
        "id": 101301,
        "matterTypeSigla": "PLO",
        "number": "11",
        "year": "2026",
        "ement": "Do Executivo",
        "authorNames": "PODER EXECUTIVO",
        "presentationDate": "2026-10-01",
    },
    {
        "id": 101302,
        "matterTypeSigla": "VETT",
        "number": "1",
        "year": "2026",
        "ement": "Veto",
        "authorNames": "Abigail Cunha",
        "presentationDate": "2026-10-01",
    },
]


def test_alema_deputados_so_em_exercicio():
    lista = alema.deputados(MA_PAGINA)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("abigail-cunha", "Abigail Cunha", "MDB"),
        ("dra-vivianne", "Dra. Vivianne", "PSD"),
    ]  # o licenciado e o cartão do topo ficam de fora


def test_alema_autoria_por_nome_exato_e_apelido_do_cadastro():
    lista = alema.deputados(MA_PAGINA)
    por_nome = alema.apelidos(MA_CADASTRO, lista)
    assert por_nome["DRA VIVIANNE"] == "dra-vivianne"
    autoria = alema.distribuir(MA_MATERIAS, por_nome)
    abigail = autoria["abigail-cunha"]
    assert abigail["tipos"] == {"Projeto de Lei": 1}
    assert abigail["projetos"][0]["id_externo"] == "PLO-269-2026"
    assert abigail["projetos"][0]["data_apresentacao"] == "2026-10-09"
    assert "  " not in abigail["projetos"][0]["ementa"]
    assert autoria["dra-vivianne"] == {"tipos": {"Indicação": 1}, "projetos": []}


@respx.mock
def test_alema_pagina_todas_as_paginas(monkeypatch):
    monkeypatch.setattr(alema, "PAUSA", 0)
    rota = respx.get(alema.API + "legislative-matter/filter/access")
    rota.side_effect = [
        httpx.Response(200, json={"content": MA_MATERIAS[:2], "totalPages": 2}),
        httpx.Response(200, json={"content": MA_MATERIAS[2:], "totalPages": 2}),
    ]
    with httpx.Client() as client:
        assert len(alema.baixar_materias(client, 2026)) == 4
    assert rota.calls[1].request.url.params["page"] == "1"


# ---------------- ALEMS ----------------
MS_PARTIDOS = """
<div class="party" >
    <div class="party-name" title="Partido Liberal">PL</div>
    <div class="party-deputies">
        <a class="party-deputy" href="/Deputados/Visualizar/6">
            <img src="/upload/Deputy/a.jpg" alt="" />
            <div class="">Coronel David </div>
        </a>
        <a class="party-deputy" href="/Deputados/Visualizar/25">
            <img src="/upload/Deputy/b.jpg" alt="" />
            <div class="">Z&#xE9; Teixeira </div>
        </a>
    </div>
</div>
<div class="party" >
    <div class="party-name" title="União Brasil">Uni&#xE3;o</div>
    <div class="party-deputies">
        <a class="party-deputy" href="/Deputados/Visualizar/50">
            <div class="">Professor Rinaldo Modesto</div>
        </a>
    </div>
</div>
"""
MS_CSV = (
    '"Portal da Transparência da Assembleia Legislativa de Mato Grosso do Sul"\n'
    '"CEAP – Cota do Exercício da Atividade Parlamentar"\n'
    '"Gerado em 09/10/2026 às 20:29 (horário de Mato Grosso do Sul)"\n'
    '"Filtros aplicados: Período: 2026 (todos os meses)"\n'
    "\n"
    'Deputado;Ano;Mês;Categoria;CPF/CNPJ;Fornecedor;Documento;Emissão;"Valor (R$)";Comprovante\n'
    '"Dep. Cel. David";2026;Março;"Combustíveis e Lubrificantes";1;"Posto";NF-1;10/03/2026;"R$ 1.200,50";http://x\n'
    '"Dep. Cel. David";2026;Março;"Combustíveis e Lubrificantes";1;"Posto";NF-2;11/03/2026;"R$ 99,50";http://x\n'
    '"Dep. Zé Teixeira";2026;Janeiro;"Divulgação";2;"Gráfica";NF-3;10/01/2026;"R$ 300,00";http://x\n'
    '"Dep.Professor Rinaldo";2026;Janeiro;"Divulgação";2;"Gráfica";NF-4;10/01/2026;"R$ 10,00";http://x\n'
    '"Dep. Neno Razuk";2026;Janeiro;"Divulgação";2;"Gráfica";NF-5;10/01/2026;"R$ 77,00";http://x\n'
)


def test_alems_deputados_por_partido():
    lista = alems.deputados(MS_PARTIDOS)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("6", "Coronel David", "PL"),
        ("25", "Zé Teixeira", "PL"),
        ("50", "Professor Rinaldo Modesto", "UNIÃO"),
    ]
    assert lista[0]["foto"] == "https://al.ms.gov.br/upload/Deputy/a.jpg"
    assert lista[2]["foto"] is None


def test_alems_ceap_soma_por_mes_e_categoria_e_conta_o_que_sobrou():
    lista = alems.deputados(MS_PARTIDOS)
    por_nome = {alems.comum.chave_nome(d["nome"]): d["id"] for d in lista}
    gastos, sem_dono = alems.gastos(MS_CSV, por_nome)
    assert gastos["6"] == [
        {
            "ano": 2026,
            "mes": 3,
            "categoria": "Combustíveis e Lubrificantes",
            "valor": Decimal("1300.00"),
        }
    ]  # "Cel. David" -> "Coronel David"; duas notas somadas
    assert gastos["25"][0]["mes"] == 1
    assert gastos["50"][0]["valor"] == Decimal("10.00")  # "Dep.Professor Rinaldo" sem espaço
    assert sem_dono == 1  # um ex-deputado


# ---------------- ALRN ----------------
RN_PAGINA = """
<div class="col-12 col-lg-4">
	<a href="https://al.rn.leg.br/deputado/77/gustavo-carvalho" class="card-deputies card-deputies-inner">
		<div class="image-deputies" style="background-image: url('https://al.rn.leg.br/storage/deputados/2023/RM.jpg')"></div>
		<strong class="name-deputies">Gustavo Carvalho</strong>
		<p class="party-deputies">Partido Liberal(PL)</p>
	</a>
</div>
<div class="col-12 col-lg-4">
	<a href="https://al.rn.leg.br/deputado/122/francisco-do-pt" class="card-deputies card-deputies-inner">
		<div class="image-deputies" style="background-image: url('https://al.rn.leg.br/storage/deputados/2023/FP.jpg')"></div>
		<strong class="name-deputies">Francisco do PT</strong>
		<p class="party-deputies">Partido dos Trabalhadores(PT)</p>
	</a>
</div>
"""
RN_CADASTRO = [
    {
        "id": 11,
        "nomeParlamentar": "DEPUTADO GUSTAVO CARVALHO",
        "iniciativas": [{"id": 10, "tipo": "PARLAMENTAR"}],
    },
    {
        "id": 12,
        "nomeParlamentar": "DEPUTADO FRANCISCO DO PT",
        "iniciativas": [{"id": 43, "tipo": "PARLAMENTAR"}, {"id": 99, "tipo": "ORGAO"}],
    },
]
RN_PROCESSOS = [
    {
        "id": 64061,
        "ano": 2026,
        "ementa": "MOÇÃO DE CONGRATULAÇÕES",
        "dataEntrada": "2026-10-08T10:46:10.527Z",
        "propositura": {"tipo": {"sigla": "REQ"}, "numero": 2127, "ano": 2026},
    },
    {
        "id": 64000,
        "ano": 2026,
        "ementa": "Institui o Dia do Cooperativismo",
        "dataEntrada": "2026-09-01T10:00:00.000Z",
        "propositura": {"tipo": {"sigla": "PL"}, "numero": 122, "ano": 2026},
    },
    {
        "id": 63999,
        "ano": 2026,
        "ementa": "Comunicado",
        "dataEntrada": "2026-08-01T10:00:00.000Z",
        "propositura": {"tipo": {"sigla": "COM"}, "numero": 292, "ano": 2026},
    },
    {
        "id": 63000,
        "ano": 2024,
        "ementa": "Antigo",
        "dataEntrada": "2024-01-01T10:00:00.000Z",
        "propositura": {"tipo": {"sigla": "PL"}, "numero": 1, "ano": 2024},
    },
]


def test_alrn_cartoes_e_iniciativas():
    lista = alrn.deputados(RN_PAGINA)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("77", "Gustavo Carvalho", "PL"),
        ("122", "Francisco do PT", "PT"),
    ]
    ids = alrn.iniciativas(RN_CADASTRO)
    assert ids["GUSTAVO CARVALHO"] == 10
    assert ids["FRANCISCO DO PT"] == 43  # só a iniciativa de parlamentar, não a do órgão


def test_alrn_classifica_projetos_e_contagem():
    tipos, projetos = alrn.classificar(RN_PROCESSOS)
    assert tipos == {"Requerimento": 1, "Projeto de Lei": 2}  # a comunicação não conta
    assert [p["id_externo"] for p in projetos] == ["PL-122-2026", "PL-1-2024"]


@respx.mock
def test_alrn_para_ao_passar_do_ano_anterior(monkeypatch):
    monkeypatch.setattr(alrn, "PAUSA", 0)
    rota = respx.get(alrn.API + "processo").mock(
        return_value=httpx.Response(200, json={"dados": RN_PROCESSOS, "total": 30000})
    )
    with httpx.Client() as client:
        achados = alrn.baixar_processos(client, 10, 2025)
    assert [p["id"] for p in achados] == [64061, 64000, 63999]
    assert rota.call_count == 1  # o último item é de 2024: não pede outra página


# ---------------- ALESE ----------------
SE_CARTAO = """
<article class="qodef-portfolio-item mix portfolio_category_887">
<div class = "qodef-item-image-holder">
<a href="https://aleselegis.al.se.leg.br/spl/parlamentar.aspx?id=426" target="_blank">
<img loading="lazy" decoding="async" width="400" height="560" src="https://al.se.leg.br/wp-content/uploads/2023/06/Luiz-Garibalde.jpg" class="attachment-full" alt="" />
</a>
</div>
<div class="qodef-item-text-holder">
<h5 class="qodef-item-title">
<a href="https://aleselegis.al.se.leg.br/spl/parlamentar.aspx?id=426" target="_blank">
Garibalde Mendon&ccedil;a			</a>
</h5>
<div class="qodef-ptf-category-holder"><span>MDB</span></div>	</div>
</article>
"""
SE_FICHA = """
<div id="tab_frequencia_plenario" class="tab-pane"><div class='kt-widget1'><div class='kt-widget1__item'>
 <div class='kt-widget1__info'>
 <h3 class='kt-widget1__title'>Presente</h3><span class='kt-widget1__desc d-block'>
 <a href='parlamentar-sessoes.aspx?x=1'><big class='align-middle'>2026</big>
 <span class='kt-badge'>134</span></a></span></div></div><div class='kt-widget1__item'>
 <div class='kt-widget1__info'>
 <h3 class='kt-widget1__title'>Falta</h3><span class='kt-widget1__desc d-block'>
 <a href='x'><big class='align-middle'>2026</big>
 <span class='kt-badge'>0</span></a></span></div></div><div class='kt-widget1__item'>
 <div class='kt-widget1__info'>
 <h3 class='kt-widget1__title'>Falta Justificada</h3><span class='kt-widget1__desc d-block'>
 <a href='x'><big class='align-middle'>2026</big>
 <span class='kt-badge'>2</span></a></span></div></div><div class='kt-widget1__item'>
 <div class='kt-widget1__info'>
 <h3 class='kt-widget1__title'>Licenciado</h3><span class='kt-widget1__desc d-block'>
 <a href='x'><big class='align-middle'>2026</big>
 <span class='kt-badge'>9</span></a></span></div></div></div></div>
"""


def test_alese_cartao_e_frequencia():
    lista = alese.deputados(SE_CARTAO)
    assert [(d["id"], d["nome"], d["partido"]) for d in lista] == [
        ("426", "Garibalde Mendonça", "MDB")
    ]
    assert alese.frequencia(SE_FICHA, 2026) == (136, 134)  # a licença não entra nas sessões
    assert alese.frequencia(SE_FICHA, 2025) == (None, None)


# ---------------- ALAP ----------------
AP_PAGINA = """
<div class="box-foto-deputados"><a href="pagina.php?pg=exibir_parlamentar&iddeputado=74" onmouseover="Tip('<b>Dep.</b> Aldilene Souza<br><b>Nome Completo:</b> ALDILENE MATOS DE SOUZA<br><b>Partido:</b> PDT<br><b>Profissão:</b> Administradora', WIDTH, 200, PADDING, 8, BGCOLOR, '#FFFFCC')"><img class="foto-deputado" src="fotodeputado/230828122115Aldilene Souza.jpg"></a></div> <p class="ls-title-5">Deputada Aldilene Souza </p>
<div class="box-foto-deputados"><a href="pagina.php?pg=exibir_parlamentar&iddeputado=75" onmouseover="Tip('<b>Dep.</b> Alliny Serrão<br><b>Nome Completo:</b> ALLINY SOUSA DA ROCHA SERRÃO<br><b>Partido:</b> UNIÃO BRASIL (UNIÃO)<br><b>Profissão:</b> Empresária ', WIDTH, 200, PADDING, 8, BGCOLOR, '#FFFFCC')"><img class="foto-deputado" src="fotodeputado/foto_alliny.jpg"></a></div>
"""
AP_TABELA = """
<tbody>
<tr>
  <td>09/10/2026</td>
  <td> Projeto de Lei Ordinária nº 0166/26-AL</td>
  <td>Deputado Carlos Lobato</td>
  <td>Institui a politica estadual de micromobilidade.</td>
  <td> <a href="https://elegis.al.ap.leg.br/portal/proposicao/111196" class="ls-btn">Visualizar</a> </td>
</tr>
<tr>
  <td>01/07/2026</td>
  <td> Veto nº 0050/26-GEA</td>
  <td>Poder Executivo</td>
  <td>Veto Total ao Projeto de Lei.</td>
  <td> <a href="https://elegis.al.ap.leg.br/portal/proposicao/110471" class="ls-btn">Visualizar</a> </td>
</tr>
</tbody>
"""


def test_alap_deputados_e_proposicoes():
    lista = alap.deputados(AP_PAGINA)
    assert [(d["id"], d["nome"], d["civil"], d["partido"]) for d in lista] == [
        ("74", "Aldilene Souza", "ALDILENE MATOS DE SOUZA", "PDT"),
        ("75", "Alliny Serrão", "ALLINY SOUSA DA ROCHA SERRÃO", "UNIÃO"),
    ]
    assert lista[0]["foto"] == "https://al.ap.leg.br/fotodeputado/230828122115Aldilene%20Souza.jpg"
    props = alap.proposicoes(AP_TABELA, "PL", "Projeto de Lei")
    assert props[0]["autor"] == "Carlos Lobato"
    assert props[0]["projeto"]["id_externo"] == "PL-166-2026"
    assert props[0]["projeto"]["data_apresentacao"] == "2026-10-09"
    assert props[1]["autor"] == "Poder Executivo"  # não casa com deputado na coleta


@respx.mock
def test_alap_baixar_para_quando_a_pagina_nao_traz_novidade(monkeypatch):
    monkeypatch.setattr(alap, "PAUSA", 0)
    rota = respx.get(alap.ELEGIS).mock(return_value=httpx.Response(200, text=AP_TABELA))
    with httpx.Client() as client:
        achados = alap.baixar(client, "1", 2026)
    assert len(achados) == 2
    assert rota.call_count == 2  # a segunda página repete as mesmas: fim


# ---------------- ALEGO ----------------
GO_PAGINA = """
<tr data-target="search.filterable" data-filter-key='amauri ribeiro pl pl'>
<td data-title="Nome"> <a class="link" href=/deputados/perfil/137>Amauri Ribeiro</a> </td>
<td data-title="Partido">PL (PL)</td>
<td data-title="Telefones"> <span><a class='link' href='tel:6232213188'>(62) 3221-3188</a></span> </td>
<td class="tab__acoes no-print"> <a href="mailto:deputadoamauriribeiro@al.go.leg.br" target="_blank">x</a> </td>
</tr>
<tr data-target="search.filterable" data-filter-key='thiago albernaz mdb'>
<td data-title="Nome"> <a class="link" href=/deputados/perfil/149>Thiago Albernaz</a> </td>
<td data-title="Partido"> MOVIMENTO DEMOCRÁTICO BRASILEIRO (MDB)</td>
<td data-title="Telefones"> </td>
</tr>
"""
GO_VERBAS = [
    {
        "id": 10345,
        "ano": 2026,
        "mes": 8,
        "valor_apresentado": "40478.2",
        "valor_indenizado": "40400.10",
        "deputado": {"id": 137, "nome": "Amauri Ribeiro"},
    },
    {
        "id": 10346,
        "ano": 2026,
        "mes": 8,
        "valor_apresentado": "1.0",
        "valor_indenizado": None,
        "deputado": {"id": 999, "nome": "Outro"},
    },
]


def test_alego_deputados_e_verbas():
    lista = alego.deputados(GO_PAGINA)
    assert [(d["id"], d["nome"], d["partido"], d["email"]) for d in lista] == [
        ("137", "Amauri Ribeiro", "PL", "deputadoamauriribeiro@al.go.leg.br"),
        ("149", "Thiago Albernaz", "MDB", None),
    ]
    v = alego.verbas(GO_VERBAS)
    assert v["137"] == [
        {"ano": 2026, "mes": 8, "categoria": "Verba indenizatória", "valor": Decimal("40400.10")}
    ]
    assert v["999"][0]["valor"] == Decimal("0")


@respx.mock
def test_alego_coleta_usa_so_os_meses_que_existem(monkeypatch):
    monkeypatch.setattr(alego, "PAUSA", 0)
    respx.get(alego.LISTA).mock(return_value=httpx.Response(200, text=GO_PAGINA))
    respx.get(alego.API + "verbas_indenizatorias/periodos").mock(
        return_value=httpx.Response(
            200, json=[{"ano": 2026, "meses": [8, 7]}, {"ano": 2018, "meses": [1]}]
        )
    )
    rota = respx.get(alego.API + "verbas_indenizatorias.json").mock(
        return_value=httpx.Response(200, json=GO_VERBAS[:1])
    )
    casa = alego.coletar(date(2026, 10, 10))
    assert rota.call_count == 2  # 2018 está fora do período; julho e agosto de 2026
    assert [len(d["gastos"]) for d in casa["vereadores"]] == [2, 0]


# ---------------- base ----------------
def test_base_registro_formato_do_gravar():
    r = base.registro(
        {
            "id": 7,
            "nome": "ZÉ DO TESTE",
            "civil": "JOSE DA SILVA",
            "partido": "PL",
            "email": " A@B.GOV.BR ",
        }
    )
    assert r["id_externo"] == "7"
    assert r["nome"] == "Zé do Teste"
    assert r["nome_completo"] == "Jose da Silva"
    assert r["email"] == "a@b.gov.br"
    assert r["em_exercicio"] is True and r["projetos"] == [] and r["gastos"] == []
    assert json.dumps(base.casa("x", [r]), default=str)
