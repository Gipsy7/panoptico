# ruff: noqa: E501  (recortes das páginas reais da ALECE)
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from ingestion.assembleias import alece, base


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


GASTOS = (Path(__file__).parent / "fixtures" / "alece_gastos_2026_08.csv").read_bytes()
SEM_LANCAMENTOS = b";;;\r\nDEPUTADO;PERIODO;EMPENHO;DESCRICAO;CNPJ;CREDOR;VALOR\r\n"


def test_categoria_pelo_texto_do_empenho():
    assert alece.categoria(
        "REFERE-SE A DISPONIBILIZACAO DO BENEFICIO ALIMENTACAO, EM AGOSTO/2026."
    ) == ("Vale-alimentação e refeição")
    # a anulação mantém o assunto, para o valor negativo abater o mesmo tipo
    assert alece.categoria(
        "ANULACAO TOTAL DA NE 2025NE000488, REFERENTE A DISPONIBILIZACAO DO BENEFICIO REFEICAO"
    ) == ("Vale-alimentação e refeição")
    assert alece.categoria(
        "REFERE-SE AO CONTRATO 13/2025, DE ... PARA ABASTECIMENTO DE COMBUSTIVEIS"
    ) == ("Combustível (cartão)")
    assert alece.categoria(
        "REFERE-SE AO REEMBOLSO DE DESPESAS INDENIZATORIAS CONFORME ATO NORMATIVO 343/24 DIVULGACAO DAS ATIVIDADES PARLAMENTARES"
    ) == ("Divulgação da atividade parlamentar")
    assert alece.categoria(
        "REFERE-SE AO REEMBOLSO DE DESPESAS INDENIZATORIAS CONFORME ATO NORMATIVO 343/24 LOCACAO DE SOFTWARE"
    ) == ("Site, software e pesquisa")
    assert alece.categoria("REFERENTE A SERVICOS DE CONSULTORIA E ASSESSORIA JURIDICA") == (
        "Consultoria e assessoria"
    )
    assert alece.categoria("REFERE-SE A ANULACAO PARCIAL DA AD 032700003, 2026NE001395") == "Outros"


def test_csv_do_mes_tem_linha_de_ponto_e_virgula_antes_do_cabecalho():
    linhas = alece.ler_mes(GASTOS)
    assert linhas[0]["DEPUTADO"] == "DEP AGENOR NETO" and linhas[0]["PERIODO"] == "08/2026"
    assert alece.ler_mes(SEM_LANCAMENTOS) == []  # mês que ainda não aconteceu
    with pytest.raises(ValueError):
        alece.ler_mes(b"<html>erro</html>")
    with pytest.raises(ValueError):
        alece.linhas_dos_arquivos({"2026-11.csv": SEM_LANCAMENTOS})  # nada em nenhum mês


def test_gastos_somam_por_deputado_mes_e_tipo_com_anulacao_abatendo():
    soma, fora = alece.somar_gastos(alece.ler_mes(GASTOS))
    assert fora == {}
    agenor = soma["AGENOR NETO"]
    assert agenor[(2026, 8, "Vale-alimentação e refeição")] == Decimal("5000.00")  # 1.000 + 4.000
    # dezembro/2025: o empenho de 2.000 e a anulação de -2.000 se cancelam
    assert soma["DRA SILVANA"][(2025, 12, "Vale-alimentação e refeição")] == Decimal("0.00")
    assert alece._valor("-16.000,00") == Decimal("-16000.00")


def test_linha_sem_periodo_ou_valor_legivel_vai_para_fora_da_soma():
    linhas = [
        {
            "DEPUTADO": "DEP AGENOR NETO",
            "PERIODO": "08/2026",
            "DESCRICAO": "X",
            "VALOR": "1.000,00",
        },
        {"DEPUTADO": "DEP AGENOR NETO", "PERIODO": "", "DESCRICAO": "X", "VALOR": "300,00"},
        {"DEPUTADO": "DEP AGENOR NETO", "PERIODO": "09/2026", "DESCRICAO": "X", "VALOR": "abc"},
    ]
    soma, fora = alece.somar_gastos(linhas)
    assert sum(soma["AGENOR NETO"].values()) == Decimal("1000.00")
    assert fora["AGENOR NETO"][0] == {
        "linhas": 1,
        "valor": Decimal("300.00"),
        "linhas_valor_ilegivel": 0,
    }
    assert fora["AGENOR NETO"][2026] == {
        "linhas": 1,
        "valor": Decimal("0"),
        "linhas_valor_ilegivel": 1,
    }


def test_ligacao_so_por_nome_exato_nunca_aproximado():
    deputados = [{"nome": "Sérgio Aguiar"}, {"nome": "Dra. Silvana"}, {"nome": "Emilia Pessoa"}]
    chaves = {
        alece.nome_do_csv(n)
        for n in (
            "DEP SERGIO AGUIAR.",
            "DEP DRA SILVANA",
            "DEP SERGIO AHUIAR",
            "DEP EMIILA PESSOA",
            "DEP ACRISIO SENA",
        )
    }
    ligados, sobras = base.ligar_nomes_exatos(chaves, deputados, [])
    assert ligados == {
        "SERGIO AGUIAR": "Sérgio Aguiar",
        "DRA SILVANA": "Dra. Silvana",
    }
    assert sobras == [
        "ACRISIO SENA",
        "EMIILA PESSOA",
        "SERGIO AHUIAR",
    ]  # erro de digitação não liga
    # via TSE: o nome civil igual ao de urna da mesma candidatura que bate com o da lista
    ligados, _ = base.ligar_nomes_exatos(
        {"EMILIA PESSOA MARTINS"}, deputados, [("Emilia Pessoa", "Emilia Pessoa Martins")]
    )
    assert ligados == {"EMILIA PESSOA MARTINS": "Emilia Pessoa"}


@respx.mock
def test_coletar_percorre_de_tras_para_frente(monkeypatch, tmp_path):
    monkeypatch.setattr(alece, "PAUSA", 0)
    monkeypatch.setattr(alece.comum, "RAW_DIR", tmp_path)
    respx.get(alece.GASTOS).respond(content=GASTOS)
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
    # os gastos: 10 meses de 2026 e 12 de 2025 até hoje (a 9/10/2026), um zip bruto guardado
    assert len(casa["linhas_gastos"]) == 22 * len(alece.ler_mes(GASTOS))
    bruto = next(tmp_path.glob("alece/gastos_*.zip"))
    with zipfile.ZipFile(bruto) as z:
        assert sorted(z.namelist())[0] == "2025-01.csv" and len(z.namelist()) == 22
