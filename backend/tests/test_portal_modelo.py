# ruff: noqa: E501  (recortes de páginas reais dos portais de Imbuia (SC) e Santana do Piauí (PI))
import json
from pathlib import Path

import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import portal_modelo, sapl
from tests.test_api import _ingestao

PAGINAS = json.loads(
    (Path(__file__).parent / "fixtures" / "portal_modelo_paginas.json").read_text(encoding="utf-8")
)
IMBUIA = "https://www.imbuia.sc.leg.br"
LISTA = "/processo-legislativo/parlamentares"
ID_ATUAL = "85306b984c0147058b8e0694cee5c564"


def test_legislatura_atual_do_seletor():
    assert portal_modelo.legislatura_atual(PAGINAS["seletor"]) == ID_ATUAL
    assert portal_modelo.legislatura_atual("<select></select>") is None


def test_ativos_ficam_e_inativos_nao():
    cartao = PAGINAS["ativos"].split("<h2>Ativos</h2>")[1].split("</li>")[0] + "</li>"
    pagina = (
        PAGINAS["ativos"] + "<h2>Inativos</h2><ul>" + cartao.replace("Aldori", "Antigo") + "</ul>"
    )
    pessoas = portal_modelo.ativos(pagina)
    assert pessoas[0] == (f"{IMBUIA}/aldori", "Aldori", "PMDB")
    assert [p[1] for p in pessoas] == ["Aldori", "Claudio"]


def test_itens_da_pasta_sem_o_link_repetido_do_leia_mais():
    itens = portal_modelo.itens_da_pasta(PAGINAS["pasta"])
    assert [nome for _, nome, _ in itens] == ["Netinho do Mel", "Antonio de Hercília"]


def test_ficha_traz_nome_civil_e_partido():
    v = portal_modelo.vereador(f"{IMBUIA}{LISTA}/claudio", "Claudio", "PP", PAGINAS["ficha_imbuia"])
    assert (v["id_externo"], v["nome"], v["nome_completo"], v["partido"]) == (
        "claudio",
        "Claudio",
        "Claudio Luiz Cordova Vargas",
        "PP",
    )
    s = portal_modelo.vereador("x/antonio-de-hercilia-1", "Antonio", "", PAGINAS["ficha_santana"])
    assert (s["nome_completo"], s["partido"]) == ("Antônio Joaquim Leal", "MDB")


@respx.mock
def test_coletar_com_seletor_e_gravar_liga_ao_eleito(monkeypatch, session):
    monkeypatch.setattr(portal_modelo, "PAUSA", 0)
    pagina = '<option value="' + ID_ATUAL + '" selected>15 (2025 - 2028) (Atual)</option>'
    lista = respx.get(IMBUIA + LISTA).respond(text=pagina)
    respx.get(f"{IMBUIA}{LISTA}/@@legislature-members", params={"legislature": ID_ATUAL}).respond(
        text=PAGINAS["ativos"]
    )
    respx.get(f"{IMBUIA}/aldori").respond(
        text=PAGINAS["ficha_imbuia"].replace("Claudio Luiz Cordova Vargas", "Aldori Fulano")
    )
    respx.get(f"{IMBUIA}{LISTA}/claudio").respond(text=PAGINAS["ficha_imbuia"])
    camara = portal_modelo.coletar(IMBUIA + "/")
    assert lista.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    assert [v["nome"] for v in camara["vereadores"]] == ["Aldori", "Claudio"]

    session.add(Municipio(ibge="4207403", nome="Imbuia", uf="SC", nome_chave="IMBUIA"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="SC", unidade="Imbuia",
                            municipio_ibge="4207403", nome="CLAUDIO LUIZ CORDOVA VARGAS", nome_urna="CLAUDIO",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "4207403", camara) == 2
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Claudio"].candidatura_id is not None and mandatos["Claudio"].partido == "PP"


@respx.mock
def test_coletar_pasta_sem_seletor(monkeypatch):
    monkeypatch.setattr(portal_modelo, "PAUSA", 0)
    base = "https://www.santanadopiaui.pi.leg.br"
    respx.get(base + LISTA).respond(text=PAGINAS["pasta"])
    respx.get(f"{base}{LISTA}/netinho-do-mel").respond(text=PAGINAS["ficha_santana"])
    respx.get(f"{base}{LISTA}/antonio-de-hercilia-1").respond(text=PAGINAS["ficha_santana"])
    camara = portal_modelo.coletar(base)
    assert [(v["nome"], v["partido"]) for v in camara["vereadores"]] == [
        ("Netinho do Mel", "MDB"),
        ("Antonio de Hercília", "MDB"),
    ]


def test_membros_da_legislatura_atual_so_ativos():
    membros = portal_modelo.membros_da_legislatura(PAGINAS["legislatura_atual"])
    assert [(m["id_externo"], m["nome"], m["nome_completo"], m["partido"]) for m in membros] == [
        ("jonas", "Jonas", "Jonas Vilarino da Rosa", "MDB"),
        ("oziel-zotti", "Oziel Zotti", None, "PSD"),
    ]
    assert portal_modelo.membros_da_legislatura(PAGINAS["legislatura_antiga"]) == []


def test_blocos_da_capa_aceitam_atributos_em_qualquer_ordem():
    blocos = portal_modelo.blocos_da_capa(PAGINAS["capa_campo_novo"])
    assert [(b[1], b[2]) for b in blocos] == [
        ("Thiago Onofre", "PODE"),
        ("Gilmário S. de Góes", "PSD"),
    ]
    assert blocos[1][0].endswith("/9a-legislatura-1/gilmario-goes")


@respx.mock
def test_coletar_pela_pasta_de_legislaturas(monkeypatch):
    monkeypatch.setattr(portal_modelo, "PAUSA", 0)
    base = "https://www.vilaflores.rs.leg.br"
    respx.get(base + LISTA).respond(text="<html>Parlamentares</html>")
    respx.get(base + portal_modelo.LEGISLATURAS).respond(
        text='<a href="x/legislaturas/9-legislatura">9</a> <a href="x/legislaturas/10">10</a>'
        '<a href="x/legislaturas/RSS">RSS</a>'
    )
    respx.get(f"{base}{portal_modelo.LEGISLATURAS}/9-legislatura").respond(
        text=PAGINAS["legislatura_antiga"]
    )
    respx.get(f"{base}{portal_modelo.LEGISLATURAS}/10").respond(text=PAGINAS["legislatura_atual"])
    camara = portal_modelo.coletar(base)
    assert [v["nome"] for v in camara["vereadores"]] == ["Jonas", "Oziel Zotti"]


@respx.mock
def test_coletar_pela_capa_quando_a_pasta_de_parlamentares_nao_existe(monkeypatch):
    monkeypatch.setattr(portal_modelo, "PAUSA", 0)
    base = "https://www.camponovoderondonia.ro.leg.br"
    respx.get(base + LISTA).respond(404)
    respx.get(base + portal_modelo.LEGISLATURAS).respond(404)
    respx.get(base + portal_modelo.CAPAS).respond(text=PAGINAS["pasta_legislaturas_campo_novo"])
    capa = f"{base}{portal_modelo.CAPAS}/9a-legislatura-1"
    respx.get(capa + "/capa").respond(text=PAGINAS["capa_campo_novo"])
    respx.get(capa + "/thiago-dos-tres-coqueiros").respond(text=PAGINAS["ficha_campo_novo"])
    respx.get(capa + "/gilmario-goes").respond(
        text=PAGINAS["ficha_campo_novo"].replace("Thiago dos Três Coqueiros", "Gilmário Góes")
    )
    camara = portal_modelo.coletar(base)
    assert [(v["nome"], v["nome_completo"], v["partido"]) for v in camara["vereadores"]] == [
        ("Thiago dos Três Coqueiros", "Thiago Onofre", "PODE"),
        ("Gilmário Góes", "Gilmário S. de Góes", "PSD"),
    ]
