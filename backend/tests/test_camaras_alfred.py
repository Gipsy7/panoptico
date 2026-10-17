# Fixtures: recortes reais das páginas de Cachoeiro de Itapemirim, Aracruz, Varjão de Minas,
# Nortelândia, Santa Maria do Cambucá e Alvorada (sem data de nascimento, telefone nem e-mail).
from pathlib import Path

import pytest
import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import fornecedores_alfred as f
from tests.test_api import _ingestao

PASTA = Path(__file__).parent / "fixtures"


def ler(nome: str) -> str:
    return (PASTA / nome).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def sem_pausa(monkeypatch):
    monkeypatch.setattr(f.time, "sleep", lambda _s: None)


def test_camarasempapel_cachoeiro_so_ativos_com_nome_civil_e_apelido():
    base = "https://cachoeiro.nopapercloud.com.br/parlamentares.aspx"
    v = f.vereadores_camarasempapel(ler("camarasempapel_cachoeiro.html"), base)
    # o recorte tem 2 ativos, 1 suplente e 1 em licença: entram só os ativos
    assert [(x["nome"], x["nome_completo"], x["partido"]) for x in v] == [
        ("Alexandre de Itaoca", "Alexandre Andreza Macedo", "PSB"),
        ("Maitan", "Alexandre Valdo Maitan", "UB"),
    ]
    assert v[0]["id_externo"] == "37"
    assert v[0]["foto_url"].startswith("https://cachoeiro.nopapercloud.com.br/arquivo/")
    assert v[0]["inicio"] == "2025-01-01" and v[0]["fim"] == "2028-12-31"


def test_camarasempapel_aracruz_nome_de_urna_em_maiusculas_vira_nome_proprio():
    v = f.vereadores_camarasempapel(
        ler("camarasempapel_aracruz.html"),
        "https://aracruz.camarasempapel.com.br/parlamentares.aspx",
    )
    assert [(x["nome"], x["partido"]) for x in v] == [
        ("Adriana Guimaraes", "MDB"),
        ("Alex Hander", "REPUBLICANOS"),
    ]
    assert all(x["nome_completo"] is None for x in v)


def test_camarasempapel_legislatura_antiga_nao_entra():
    antiga = ler("camarasempapel_aracruz.html").replace(
        "01/01/2025 a 31/12/2028", "01/01/2021 a 31/12/2024"
    )
    assert f.vereadores_camarasempapel(antiga, "https://x/") == []


def test_webline_varjao_nome_e_sigla_do_partido():
    v = f.vereadores_webline(ler("webline_varjao.html"), "https://varjaodeminas.mg.leg.br/")
    assert [(x["id_externo"], x["nome"], x["partido"]) for x in v] == [
        ("21", "Expedito Alves Pereira Neto", "SD"),
        ("14", "Jader Borges Silva", "PP"),
        ("8", "José dos Reis Braga", "PL"),
    ]


def test_nortelandia_sigla_antes_do_nome_do_partido_e_foto_na_raiz():
    v = f.vereadores_nortelandia(
        ler("nortelandia.html"), "https://nortelandia.mt.leg.br/camara/vereadores"
    )
    assert [(x["id_externo"], x["nome"], x["partido"]) for x in v] == [
        ("12", "Flávio Vinícius Fonseca de Sá", "PSB"),
        ("16", "Domival Rodrigues Silva Júnior", "PSB"),
        ("13", "Elka Beatriz Monteiro e Mayer", "MDB"),
    ]
    assert v[0]["foto_url"].startswith("https://nortelandia.mt.leg.br/publico/servidores/")


def test_cambuca_json_so_nome_foto_e_situacao():
    assert f.legislatura_cambuca(ler("cambuca_pagina.html")) == "22"
    v = f.vereadores_cambuca(
        ler("cambuca.json"), "https://transparencia.santamariadocambuca.pe.leg.br/vereadores.php"
    )
    assert [(x["nome"], x["nome_completo"], x["partido"]) for x in v] == [
        ("Xinha de Judite", "Carlos Caetano da Silva Neto", None),
        ("Edinho de Nofa", "Edilson Pereira da Silva", None),
    ]
    assert v[0]["foto_url"].startswith(
        "https://transparencia.santamariadocambuca.pe.leg.br/sistema/uploads/parlamentares/"
    )
    assert all(x["email"] is None and x["telefone"] is None for x in v)


def test_alvorada_tira_cargo_da_mesa_e_acerta_apelido_e_partido():
    v = f.vereadores_alvorada(
        ler("alvorada.html"), "https://alvorada.to.leg.br/transparencia/vereador"
    )
    por_nome = {x["nome"]: x for x in v}
    assert por_nome["Derli Pellenz"]["partido"] == "UNIÃO"  # "UNIÃO BRASIL" no site
    assert "Leonardo Viegas Rinaldi" in por_nome  # sem o " - 1º Secretário"
    greice = por_nome["Greice Do Postinho"]
    assert greice["nome_completo"] == "Grace Karen Marques dos Reis"
    assert greice["partido"] == "PDT"


def test_decodifica_utf8_declarado_com_bytes_latin1():
    assert f._decodificar("Léo Pereira".encode("cp1252")) == "Léo Pereira"
    assert f._decodificar("Léo Pereira".encode()) == "Léo Pereira"


@respx.mock
def test_coletar_respeita_o_robots_e_nao_faz_o_pedido_vedado():
    respx.get("https://varjaodeminas.mg.leg.br/robots.txt").respond(
        text="User-agent: *\nDisallow: /"
    )
    pagina = respx.get("https://varjaodeminas.mg.leg.br/").respond(text=ler("webline_varjao.html"))
    with pytest.raises(PermissionError):
        f.coletar("https://varjaodeminas.mg.leg.br/", "webline")
    assert not pagina.called


@respx.mock
def test_coletar_cambuca_faz_duas_requisicoes_com_user_agent_identificado():
    base = "https://transparencia.santamariadocambuca.pe.leg.br/"
    respx.get(base + "robots.txt").respond(text="User-agent: *\nAllow: /\n")
    pagina = respx.get(base + "vereadores.php").respond(text=ler("cambuca_pagina.html"))
    lista = respx.get(base + "vereadoresClass.php").respond(text=ler("cambuca.json"))
    camara = f.coletar(base + "vereadores.php", "cambuca")
    assert len(camara["vereadores"]) == 2
    assert lista.calls[0].request.url.params["legislatura"] == "22"
    assert pagina.calls[0].request.headers["User-Agent"].startswith("Panoptico")


@respx.mock
def test_coletar_e_gravar_liga_ao_eleito(session):
    base = "https://alvorada.to.leg.br/"
    respx.get(base + "robots.txt").respond(text="<!DOCTYPE html><html></html>")  # sem regras
    respx.get(base + "transparencia/vereador").respond(text=ler("alvorada.html"))
    camara = f.coletar(base + "transparencia/vereador", "alvorada")
    session.add(Municipio(ibge="1700707", nome="Alvorada", uf="TO", nome_chave="ALVORADA"))
    session.flush()
    session.add(
        Candidatura(
            ano_eleicao=2024,
            sq_candidato="1",
            cargo="VEREADOR",
            uf="TO",
            unidade="Alvorada",
            municipio_ibge="1700707",
            nome="DERLI PELLENZ",
            nome_urna="DERLI PELLENZ",
            situacao_turno="ELEITO POR QP",
            ingestao_id=_ingestao(session).id,
        )
    )
    session.flush()
    from ingestion.camaras import sapl

    assert sapl.gravar(session, "1700707", camara) == 3
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Derli Pellenz"].candidatura_id is not None
    assert mandatos["Greice Do Postinho"].candidatura_id is None


def test_fonte_citada_no_site_e_a_deste_conector():
    from app.services.camaras import _fonte

    for _ibge, _cidade, _modelo, url in f.CAMARAS:
        assert _fonte("camara", "XX", url)[0] == "fornecedores_alfred_camaras", url


def test_lista_de_camaras_tem_modelo_conhecido():
    modelos = {"camarasempapel", "webline", "nortelandia", "cambuca", "alvorada"}
    assert {c[2] for c in f.CAMARAS} == modelos
    assert len({c[0] for c in f.CAMARAS}) == len(f.CAMARAS)
