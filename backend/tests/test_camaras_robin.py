# ruff: noqa: E501
"""Leitores de Senador Guiomard (Wix) e Praia Grande (e-Solution); recortes reais em fixtures/."""

from pathlib import Path

import pytest
import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import fornecedores_robin as robin
from ingestion.camaras import sapl
from tests.test_api import _ingestao

FIXTURES = Path(__file__).parent / "fixtures"
WIX = (FIXTURES / "senador_guiomard_vereadores.html").read_text(encoding="utf-8")
ESOLUTION = (FIXTURES / "praia_grande_bandeiras.json").read_text(encoding="utf-8")


def test_wix_nome_civil_apelido_partido_e_ignora_outros_blocos():
    por_id = {v["id_externo"]: v for v in robin.vereadores_wix(WIX)}
    assert len(por_id) == 4  # o bloco "Menu" não tem link de vereador
    williene = por_id["williene-magda--297a"]
    assert (williene["nome"], williene["nome_completo"], williene["partido"]) == (
        "Williene Magda Novais Jardim",
        None,
        "PL",
    )
    assert williene["foto_url"] is None  # imagem padrão do Wix ("empty-state")


def test_wix_apelido_entre_parenteses_vira_o_nome():
    por_nome = {v["nome"]: v for v in robin.vereadores_wix(WIX)}
    lenon = por_nome["Lenon"]
    assert lenon["nome_completo"] == "Elvys Lenon Nascimento Araújo"
    assert lenon["partido"] == "PP"
    assert por_nome["Leiri do Mixico"]["partido"] == "REPUBLICANOS"  # "Republicanos" -> sigla


def test_wix_link_com_acento_e_desfeito_e_partido_composto_vira_sigla():
    joao = next(v for v in robin.vereadores_wix(WIX) if v["nome"].startswith("João"))
    assert joao["id_externo"].startswith("joão-rafae")
    assert joao["partido"] == "UNIÃO"  # "União Brasil"


def test_esolution_le_so_o_bloco_de_vereadores():
    vereadores = robin.vereadores_esolution(ESOLUTION)
    assert [(v["id_externo"], v["nome"], v["partido"]) for v in vereadores] == [
        ("1354", "Beto Rossi", "PSD"),
        ("1332", "Dr. Marcelo Cruz", "PL"),
        ("1345", "Renata Zabeu", "PSD"),
    ]
    assert all(v["foto_url"] is None for v in vereadores)  # /datafiles/ é vetado no robots.txt
    assert all(v["em_exercicio"] and v["inicio"] == "2025-01-01" for v in vereadores)


def test_esolution_sem_bloco_de_vereadores_devolve_lista_vazia():
    assert robin.vereadores_esolution('{"code": 200, "bandeiras": []}') == []


@respx.mock
def test_coletar_wix_e_esolution_com_user_agent_identificado():
    sg = respx.get("https://www.senadorguiomard.ac.leg.br/vereadores").respond(text=WIX)
    pg = respx.get(
        "https://www.praiagrande.sp.leg.br/publico/service/onepage/select.geral.bandeiras.php"
    ).respond(text=ESOLUTION)
    assert len(robin.coletar("https://www.senadorguiomard.ac.leg.br/", "wix")["vereadores"]) == 4
    assert len(robin.coletar("https://www.praiagrande.sp.leg.br", "esolution")["vereadores"]) == 3
    assert sg.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    assert pg.call_count == 1


def test_leitor_desconhecido_falha():
    with pytest.raises(ValueError):
        robin.coletar("https://exemplo.leg.br", "outro")


@respx.mock
def test_gravar_liga_ao_eleito_do_tse(session):
    respx.get(
        "https://www.praiagrande.sp.leg.br/publico/service/onepage/select.geral.bandeiras.php"
    ).respond(text=ESOLUTION)
    camara = robin.coletar("https://www.praiagrande.sp.leg.br", "esolution")
    session.add(Municipio(ibge="3541000", nome="Praia Grande", uf="SP", nome_chave="PRAIA GRANDE"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="SP", unidade="Praia Grande",
                            municipio_ibge="3541000", nome="RENATA ZABEU LUZ", nome_urna="RENATA ZABEU",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()

    assert sapl.gravar(session, "3541000", camara) == 3
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Renata Zabeu"].candidatura_id is not None
    assert mandatos["Beto Rossi"].partido == "PSD"
