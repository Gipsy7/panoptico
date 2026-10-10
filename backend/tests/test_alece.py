# ruff: noqa: E501  (recortes das páginas reais da ALECE)
from datetime import date

import httpx
import respx

from ingestion.assembleias import alece


def _cartao(slug, nome, partido, estado=""):
    return f"""
<div
    class="deputado_card {estado}"
    style="max-width: 300px"
>
    <img
        width="100%"
        src="https://www.al.ce.gov.br/image/389109"
        alt="Foto de {nome}"
    >

    <p class="deputado_card--nome s-font-1"><a href="https://www.al.ce.gov.br/deputados/{slug}">                            {nome} </a></p>
    <p class="deputado_card--partido s-font-1"> {partido} </p>
</div>"""


LISTA = (
    '<h1 class="main_page--title">Em Exercício e <span style="color:red">Licenciados</span></h1>'
    + _cartao("agenor-neto", "Agenor Neto", "MDB")
    + _cartao("guilherme-landim", "Guilherme Landim", "PSB", "licenciado")
    + _cartao("agenor-neto", "Agenor Neto", "MDB")  # repetido
    + '<h2 class="main_page--title mt-lg-5">Suplentes em Exercício</h2>'
    + _cartao("antonio-granja", "Antônio Granja", "PSB")
)
FICHA = """
<div class="d-flex flex-column mt-2"> <span class="font-weight-bold"> E-mails </span> <span class="text-gray-accessible"> Gabdepagenor.neto@al.ce.gov.br </span> </div>
<div class="d-flex flex-column mt-2"> <span class="font-weight-bold"> Telefones </span> <span class="text-gray-accessible"> 3277 2572 / 3277 2503 </span> </div>
"""


def _registro(
    numero,
    autor,
    entrada,
    obs="TRAMITANDO",
    ementa="INSTITUI O DIA ESTADUAL.",
    link="https://www2.al.ce.gov.br/legislativo/tramit2026/pl1_26.pdf",
):
    return f"""<tr><td width='100%'><table><tr>
<td width='15%'><font face='Verdana' size='1' color='#000000'><b>N&ordm; do Proj.:</b></font><br><font face='Verdana' size='1'>{numero} </font></td>
<td width='55%'><font face='Verdana' size='1' color='#000000'><b>Autor:</b></font><br><font face='Verdana' size='1'>{autor}</font></td>
<td width='16%'><font face='Verdana' size='1' color='#000000'><b>Entrada:</b></font><br><font face='Verdana' size='1'>{entrada}</font></td></tr></table></td></tr>
<tr><td><font face='Verdana' size='1' color='#000000'><b>Ementa:</b></font><br><font face='Verdana' size='1'><a href='{link}'>{ementa}</a></font></td></tr>
<tr><td><font face='Verdana' size='1' color='#000000'><b>OBS:</b></font><br><font face='Verdana' size='1'>{obs}</font></td></tr>"""


def test_lista_de_deputados_com_licenciados_e_suplentes():
    lista = alece.deputados(LISTA)
    assert [(d["slug"], d["partido"], d["licenciado"], d["suplente"]) for d in lista] == [
        ("agenor-neto", "MDB", False, False),
        ("guilherme-landim", "PSB", True, False),
        ("antonio-granja", "PSB", False, True),
    ]
    assert lista[2]["nome"] == "Antônio Granja"


def test_ficha_e_autores():
    assert alece.ficha(FICHA) == {
        "email": "gabdepagenor.neto@al.ce.gov.br",
        "telefone": "3277 2572 / 3277 2503",
    }
    assert alece.ficha("<html></html>") == {"email": None, "telefone": None}
    assert alece._autores("AUTORIA: DEPUTADA EMILIA PESSOA.") == ["EMILIA PESSOA"]
    assert alece._autores("Autoria: Deputado Fernando Santana.") == ["Fernando Santana"]
    assert alece._autores("LARISSA GASPAR") == ["LARISSA GASPAR"]
    assert alece._autores("DEPUTADOS AGENOR NETO E LIA GOMES") == ["AGENOR NETO", "LIA GOMES"]


def test_proposicoes_da_listagem():
    pagina = (
        _registro("572/26", "AUTORIA: DEPUTADO BRUNO PEDROSA.", "31.08.2026")
        + _registro("9/24", "LARISSA GASPAR", "04.02.24", obs="ARQUIVADO")
        + _registro("572/256", "X", "26.06.25")  # linha torta da fonte: ignorada
    )
    lista = alece.proposicoes(pagina)
    assert [(p["numero"], p["ano"], p["autores"], p["entrada"], p["situacao"]) for p in lista] == [
        (572, 2026, ["BRUNO PEDROSA"], "2026-08-31", "TRAMITANDO"),
        (9, 2024, ["LARISSA GASPAR"], "2024-02-04", "ARQUIVADO"),
    ]
    assert lista[0]["ementa"] == "INSTITUI O DIA ESTADUAL."


@respx.mock
def test_coletar_percorre_de_tras_para_frente(monkeypatch):
    monkeypatch.setattr(alece, "PAUSA", 0)
    respx.get(alece.LISTA).respond(text=LISTA)
    respx.get(f"{alece.LISTA}/agenor-neto").respond(text=FICHA)
    respx.get(f"{alece.LISTA}/guilherme-landim").respond(text="")
    respx.get(f"{alece.LISTA}/antonio-granja").respond(text="")
    links = "".join(f"<a href='x?absolutepage={n}'>{n}</a>" for n in (2, 3))
    paginas = {
        None: _registro("1/23", "AGENOR NETO", "06.02.23") + links,
        "2": _registro("2/25", "AGENOR NETO", "10.03.25") + _registro("3/23", "LIA", "01.01.23"),
        "3": _registro("10/26", "AUTORIA: DEPUTADO AGENOR NETO.", "31.08.2026")
        + _registro("11/26", "GUILHERME LANDIM", "01.09.2026"),
    }
    chamadas = []

    def listagem(request):
        n = request.url.params.get("absolutepage")
        if request.url.params["tabela"] == "projeto_lei":
            chamadas.append(n)
            return httpx.Response(200, text=paginas[n])
        return httpx.Response(200, text="")

    respx.get(alece.LEGADO + "ano.php").side_effect = listagem
    casa = alece.coletar(date(2026, 10, 9))
    assert chamadas == [None, "3", "2"]  # a página 1 só tem 2023: não pede mais nada
    agenor, landim, granja = casa["vereadores"]
    assert [p["id_externo"] for p in agenor["projetos"]] == ["PL-10-2026", "PL-2-2025"]
    assert agenor["proposicoes_por_tipo"] == {"Projeto de Lei": 2}
    assert agenor["projetos"][0]["url"].startswith(
        "https://www2.al.ce.gov.br/legislativo/tramit2026/"
    )
    assert len(landim["projetos"]) == 1 and landim["em_exercicio"] is False
    assert granja["titular"] is False and granja["em_exercicio"] is True
    assert agenor["email"] == "gabdepagenor.neto@al.ce.gov.br"
