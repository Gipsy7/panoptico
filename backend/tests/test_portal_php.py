# ruff: noqa: E501  (recortes de páginas reais dos sites das câmaras de Fortim, Poranga e Amapá)
import json
from pathlib import Path

import respx
from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Municipio
from ingestion.camaras import portal_php, sapl
from tests.test_api import _ingestao

PAGINAS = json.loads(
    (Path(__file__).parent / "fixtures" / "portal_php_fichas.json").read_text(encoding="utf-8")
)
BASE = "https://fortim.ce.leg.br/vereadores"


def test_ids_da_lista_sem_repetir():
    assert portal_php.ids_da_lista(PAGINAS["lista"]) == ["26", "4", "33"]


def test_vereador_em_exercicio_com_partido_e_nome_civil():
    v = portal_php.ficha(PAGINAS["betim_fortim"], BASE, "26")
    assert (v["nome"], v["nome_completo"], v["partido"]) == (
        "Betim",
        "Carlos Alberto Scipião",
        "MDB",
    )
    assert (v["em_exercicio"], v["titular"]) == (True, True)
    assert (v["inicio"], v["fim"]) == ("2025-01-01", "2028-12-31")
    assert v["foto_url"] == "https://fortim.ce.leg.br/imagens/26.jpg"


def test_mesa_diretora_aberta_conta_como_exercicio_e_a_encerrada_nao():
    # Cargo de mesa sem data de fim na legislatura atual: é vereador em exercício.
    cicero = portal_php.ficha(
        PAGINAS["cicero_poranga"], "https://poranga.ce.leg.br/vereadores", "9"
    )
    assert cicero["partido"] == "PT" and cicero["inicio"] == "2025-01-01"
    # Só um cargo de mesa que acabou em 30/09/2025 (Fortim): fora.
    assert portal_php.ficha(PAGINAS["beto_fortim_mesa_encerrada"], BASE, "4") is None


def test_ex_vereador_de_legislatura_antiga_fica_de_fora():
    assert portal_php.ficha(PAGINAS["tica_poranga_so_antigo"], BASE, "8") is None
    assert portal_php.ficha(PAGINAS["duquinha_poranga_licenciado_antigo"], BASE, "15") is None


def test_ficha_do_amapa():
    v = portal_php.ficha(PAGINAS["diego_amapa"], "https://amapa.ap.leg.br/vereadores", "3")
    assert (v["nome"], v["nome_completo"], v["partido"]) == (
        "Diego Monteiro",
        "Diego Monteiro Melo",
        "PL",
    )


@respx.mock
def test_coletar_e_gravar_liga_ao_eleito(monkeypatch, session):
    monkeypatch.setattr(portal_php, "PAUSA", 0)
    lista = respx.get(BASE).respond(text=PAGINAS["lista"])
    respx.get(f"{BASE}/26").respond(text=PAGINAS["betim_fortim"])
    respx.get(f"{BASE}/4").respond(text=PAGINAS["beto_fortim_mesa_encerrada"])
    respx.get(f"{BASE}/33").respond(text=PAGINAS["cicero_poranga"])
    camara = portal_php.coletar(BASE)
    assert lista.calls[0].request.headers["User-Agent"].startswith("Panoptico")
    assert [v["id_externo"] for v in camara["vereadores"]] == ["26", "33"]

    session.add(Municipio(ibge="2304459", nome="Fortim", uf="CE", nome_chave="FORTIM"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="CE", unidade="Fortim",
                            municipio_ibge="2304459", nome="CARLOS ALBERTO SCIPIÃO", nome_urna="BETIM",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "2304459", camara) == 2
    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["Betim"].candidatura_id is not None
    assert mandatos["Betim"].partido == "MDB" and mandatos["Betim"].em_exercicio
    assert sapl.gravar(session, "2304459", camara) == 2  # regravar não duplica
    assert len(list(session.scalars(select(MandatoLocal)))) == 2
