# ruff: noqa: E501  (recortes de páginas reais dos portais de Pirenópolis, Cariri e Santa Rita do Tocantins)
import json
from pathlib import Path

import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import nucleogov, sapl
from tests.test_api import _ingestao

PAGINAS = json.loads(
    (Path(__file__).parent / "fixtures" / "nucleogov_paginas.json").read_text(encoding="utf-8")
)
HOME = "https://pirenopolis.go.leg.br/"


def test_links_da_pagina_inicial_sem_repetir_e_so_de_fichas():
    links = nucleogov.links_da_pagina_inicial(PAGINAS["home"])
    assert links[0] == "https://pirenopolis.go.leg.br/vereador/adalberto-moreira/"
    assert links.count("https://pirenopolis.go.leg.br/vereador/lola/") == 1
    assert all("/vereador/" in link for link in links)


def test_ficha_do_tema_com_h1_e_rotulos():
    v = nucleogov.ficha(PAGINAS["ficha_a"], "https://pirenopolis.go.leg.br/vereador/lola/")
    assert (v["id_externo"], v["nome"], v["partido"]) == (
        "lola",
        "Ana Abadia Feliciana Triers",
        "PSDB",
    )
    assert (v["titular"], v["em_exercicio"]) == (True, True)
    assert v["foto_url"] == "https://pirenopolis.go.leg.br/wp-content/uploads/2024/03/Lola.png"
    assert v["email"] is None and v["telefone"] is None  # contato não é guardado


def test_partido_do_site_vai_como_esta_mesmo_desatualizado():
    # Cariri ainda mostra "DEM" (extinto em 2022): guardamos o que a câmara informa.
    v = nucleogov.ficha(
        PAGINAS["ficha_cariri_dem"], "https://x.to.leg.br/vereador/junior-chaveiro/"
    )
    assert (v["nome"], v["partido"]) == ("Agmar Moreira Ramos Júnior", "DEM")


def test_ficha_do_tema_araguaia_tira_o_prefixo_e_le_o_nome_civil():
    v = nucleogov.ficha(
        PAGINAS["ficha_b"], "https://x.to.leg.br/vereador/ver-adelman-pereira-da-silva/"
    )
    assert (v["nome"], v["nome_completo"], v["partido"]) == (
        "Adelman Pereira da Silva",
        None,
        "REPUBLICANOS",
    )


def test_pagina_sem_nome_nao_vira_vereador():
    assert nucleogov.ficha("<html><body>nada</body></html>", HOME) is None


@respx.mock
def test_coletar_e_gravar_liga_ao_eleito(monkeypatch, session):
    monkeypatch.setattr(nucleogov, "PAUSA", 0)
    home = '<a href="https://pirenopolis.go.leg.br/vereador/lola/">Ana</a><a href="https://pirenopolis.go.leg.br/vereador/lola/">Ana</a>'
    inicial = respx.get(HOME).respond(text=home)
    respx.get("https://pirenopolis.go.leg.br/vereador/lola/").respond(text=PAGINAS["ficha_a"])
    camara = nucleogov.coletar(HOME)
    assert inicial.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    assert [v["id_externo"] for v in camara["vereadores"]] == ["lola"]
    assert camara["base"] == "https://pirenopolis.go.leg.br/vereador/"

    session.add(Municipio(ibge="5217302", nome="Pirenópolis", uf="GO", nome_chave="PIRENOPOLIS"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="GO", unidade="Pirenópolis",
                            municipio_ibge="5217302", nome="ANA ABADIA FELICIANA TRIERS", nome_urna="LOLA",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "5217302", camara) == 1
    mandato = session.scalars(select(MandatoLocal)).one()
    assert mandato.candidatura_id is not None and mandato.partido == "PSDB"
    assert sapl.gravar(session, "5217302", camara) == 1  # regravar não duplica
    assert len(list(session.scalars(select(MandatoLocal)))) == 1


def test_partido_por_extenso_vira_sigla():
    # Santa Rita informa "Partido Democrático Trabalhista – PDT" e "AGIR – Agir" (a coluna tem 30).
    assert nucleogov.sigla("Partido Democrático Trabalhista – PDT") == "PDT"
    assert nucleogov.sigla("AGIR – Agir") == "AGIR"
    assert nucleogov.sigla("UNIÃO BRASIL") == "UNIÃO BRASIL"
    assert nucleogov.sigla("") == ""


def test_prefixo_ver_do_titulo_nao_come_nome_que_comeca_com_vera():
    pagina = '<h2 class="wp-block-post-title">{}</h2>'
    for titulo, esperado in [
        ("Ver.Juraci Nunes de Carvalho", "Juraci Nunes de Carvalho"),
        ("Verª. Magda Lúcia Pereira Lima", "Magda Lúcia Pereira Lima"),
        ("Vera Lúcia Souza", "Vera Lúcia Souza"),
    ]:
        assert nucleogov.ficha(pagina.format(titulo), HOME)["nome"] == esperado
