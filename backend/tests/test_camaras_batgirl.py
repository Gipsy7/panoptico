# ruff: noqa: E501
"""Recortes reais das páginas de Pimenta Bueno (Instar), Perdões (Legislador) e Santa Cruz (WordPress)."""

from pathlib import Path

import pytest
import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import fornecedores_batgirl as f
from ingestion.camaras import sapl
from tests.test_api import _ingestao

PASTA = Path(__file__).parent / "fixtures"


def _ler(nome: str) -> str:
    return (PASTA / nome).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(f.time, "sleep", lambda _s: None)


def test_instar_usa_o_nome_de_urna_dos_dados_abertos():
    vereadores = f.vereadores_instar(
        _ler("instar_capa.html"),
        "https://www.pimentabueno.ro.leg.br/",
        _ler("instar_dados_abertos.json"),
    )
    assert [(v["id_externo"], v["nome"], v["nome_completo"], v["partido"]) for v in vereadores] == [
        ("4", "Fabio Tiziu", "Fabio Rodrigues da Silva", "PL"),
        ("6", "Fábio Matias", "Fábio Alves Matias Lemes", "União Brasil"),
    ]
    assert (
        vereadores[0]["foto_url"]
        == "https://www.pimentabueno.ro.leg.br/fotos/da99008ba94a63bd80d502e82cc7f22d.jpg"
    )
    assert (vereadores[0]["inicio"], vereadores[0]["fim"]) == ("2025-01-01", "2028-12-31")


def test_instar_sem_dados_abertos_cai_no_nome_da_capa():
    vereadores = f.vereadores_instar(_ler("instar_capa.html"), "https://x.leg.br/")
    assert [v["nome"] for v in vereadores] == ["Fabio Silva", "Fábio Lemes"]


def test_instar_recusa_legislatura_antiga():
    capa = _ler("instar_capa.html").replace("01/01/2025 - 31/12/2028", "01/01/2021 - 31/12/2024")
    with pytest.raises(ValueError, match="2025-2028"):
        f.vereadores_instar(capa, "https://x.leg.br/")


def test_legislador_le_nome_e_id_sem_guardar_a_foto_assinada():
    vereadores = f.vereadores_legislador(_ler("legislador_capa.html"), "https://x.leg.br/")
    assert [(v["id_externo"], v["nome"], v["partido"], v["foto_url"]) for v in vereadores] == [
        ("ver3", "Artur Ferreira Neto", None, None),
        ("ver1", "Anderson Carvalho Pereira", None, None),
    ]


def test_wordpress_menu_traz_o_link_https_e_nao_repete():
    capa = _ler("santacruz_menu.html") + _ler("santacruz_menu.html")
    assert [(slug, nome) for _, slug, nome in f.links_wordpress(capa)] == [
        ("bruno-leonel-da-silva-oliveira", "Bruno Leonel da Silva Oliveira"),
        ("maidjane-melo-da-silva-siqueira", "Maidjane Melo da Silva Siqueira"),
        ("telvando-rodrigues", "Telvando Rodrigues"),
    ]


def test_wordpress_ficha_nome_civil_partido_e_foto():
    telvando = f.ficha_wordpress(
        _ler("santacruz_ficha_telvando.html"), "telvando-rodrigues", "Telvando Rodrigues"
    )
    assert (telvando["nome"], telvando["nome_completo"], telvando["partido"]) == (
        "Telvando Rodrigues",
        "Telvando Rodrigues Soares",
        "AVANTE",
    )
    assert telvando["foto_url"].endswith("VEREADOR-TELVANDO-2-1-200x300.jpg")
    # O nome em negrito da ficha de Bruno é mais curto que o do menu: não vira nome completo.
    bruno = f.ficha_wordpress(
        _ler("santacruz_ficha_bruno.html"),
        "bruno-leonel-da-silva-oliveira",
        "Bruno Leonel da Silva Oliveira",
    )
    assert (bruno["nome_completo"], bruno["partido"]) == (None, "AVANTE")


@respx.mock
def test_coletar_perdoes_com_user_agent_identificado():
    pagina = respx.get("https://www.perdoes.mg.leg.br/").respond(text=_ler("legislador_capa.html"))
    camara = f.coletar("https://www.perdoes.mg.leg.br", "legislador")
    assert pagina.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    assert len(camara["vereadores"]) == 2
    assert camara["base"] == "https://www.perdoes.mg.leg.br/"


@respx.mock
def test_coletar_santa_cruz_le_a_capa_e_uma_ficha_por_vereador():
    respx.get("http://santacruz.pe.leg.br/").respond(text=_ler("santacruz_menu.html"))
    respx.get("http://santacruz.pe.leg.br/vereador/bruno-leonel-da-silva-oliveira/").respond(
        text=_ler("santacruz_ficha_bruno.html")
    )
    respx.get("https://santacruz.pe.leg.br/vereador/maidjane-melo-da-silva-siqueira/").respond(
        text=_ler("santacruz_ficha_bruno.html")
    )
    respx.get("http://santacruz.pe.leg.br/vereador/telvando-rodrigues/").respond(
        text=_ler("santacruz_ficha_telvando.html")
    )
    camara = f.coletar("http://santacruz.pe.leg.br/", "wordpress_vereador")
    assert [v["nome"] for v in camara["vereadores"]] == [
        "Bruno Leonel da Silva Oliveira",
        "Maidjane Melo da Silva Siqueira",
        "Telvando Rodrigues",
    ]


@respx.mock
def test_coletar_pimenta_bueno_e_gravar_liga_ao_eleito(session):
    respx.get("https://www.pimentabueno.ro.leg.br/").respond(text=_ler("instar_capa.html"))
    respx.route(
        method="GET", host="www.pimentabueno.ro.leg.br", path__startswith="/portal/dados-abertos/"
    ).respond(text=_ler("instar_dados_abertos.json"))
    camara = f.coletar("https://www.pimentabueno.ro.leg.br/", "instar")
    session.add(
        Municipio(ibge="1100189", nome="Pimenta Bueno", uf="RO", nome_chave="PIMENTA BUENO")
    )
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="RO", unidade="Pimenta Bueno",
                            municipio_ibge="1100189", nome="FABIO RODRIGUES DA SILVA", nome_urna="FABIO TIZIU",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "1100189", camara) == 2
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Fabio Tiziu"].candidatura_id is not None
    assert mandatos["Fábio Matias"].candidatura_id is None
