# ruff: noqa: E501
"""Leitores de fornecedores que cobrem várias câmaras (webservicesistemas, sts, cespro, icamaras,
portalfacil, ingadigital); recortes reais em fixtures/ (páginas de 21 a 27/10/2026)."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from ingestion.camaras import fornecedores_cobertura as fc

FIXTURES = Path(__file__).parent / "fixtures"


def _ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def test_partido_aceita_os_jeitos_de_escrever_e_recusa_o_que_nao_e_partido():
    assert fc.partido("PARTIDO PP") == "PP"
    assert fc.partido("Progressistas (PP)") == "PP"
    assert fc.partido("Partido dos Trabalhadores (PT)") == "PT"
    assert fc.partido("União Brasil") == "UNIÃO"
    assert fc.partido("Movimento Demorático Brasileiro") is None  # grafia errada na fonte
    assert fc.partido("Data de Nascimento: 02/01/2026") is None
    assert fc.partido("Silva") is None  # nome não vira partido


def test_nome_e_partido_separa_sigla_colada_cargo_e_licenca():
    assert fc.nome_e_partido("Joel Welter-pt") == ("Joel Welter", "PT")
    assert fc.nome_e_partido("Cerineu dos Santos - MDB - SEGUNDO SECRETÁRIO") == (
        "Cerineu dos Santos",
        "MDB",
    )
    assert fc.nome_e_partido("Sicmar Luís Stumm (PT)") == ("Sicmar Luís Stumm", "PT")
    assert fc.nome_e_partido("ADÃO MOREIRA SILVA - LICENCIADO") == ("Adão Moreira Silva", None)
    assert fc.nome_e_partido("Aparecido Moreira da Costa - Psdb/cidadania") == (
        "Aparecido Moreira da Costa",
        "PSDB",
    )
    assert fc.nome_e_partido("Maria Silva - Silva") == ("Maria Silva - Silva", None)


def test_webservices_le_so_os_publicados_com_partido_e_nome_de_urna():
    achados = fc.vereadores_webservices(_ler("webservicesistemas_vereadores.json"), "")
    assert len(achados) == 4  # o quinto registro é rascunho (status draft)
    chico = next(v for v in achados if v["id_externo"] == "107")
    assert (chico["nome"], chico["nome_completo"], chico["partido"]) == (
        "Chico Branco",
        "Francisco das Chagas Martins dos Santos",
        "UNIÃO",
    )
    assert all(v["email"] is None and v["telefone"] is None for v in achados)


def test_sts_le_a_tabela_com_nome_civil_nome_parlamentar_e_partido():
    achados = fc.vereadores_sts(_ler("sts_parlamentares.html"), "")
    assert [(v["id_externo"], v["nome"], v["partido"]) for v in achados][:2] == [
        ("49", "Caitana Oliveira", "PT"),
        ("48", "Carlin Ramos", "PT"),
    ]
    assert achados[0]["nome_completo"] == "Caitana Inácia de Oliveira"


def test_icamaras_nao_marca_ninguem_em_exercicio_antes_da_confirmacao_do_tse():
    achados = fc.vereadores_icamaras(_ler("icamaras_vereadores.html"), "")
    por_nome = {v["nome"]: v for v in achados}
    assert por_nome["Alberto de Mozzi"]["partido"] == "MDB"
    assert por_nome["Volmir Luis Gomes"]["partido"] == "PSDB"
    assert not any(v["em_exercicio"] or v["titular"] for v in achados)
    assert "Henrique Echer" in por_nome  # caixa alta no site virou nome próprio


def test_icamaras_confirma_so_quem_foi_eleito_vereador_na_cidade(session):
    from app.models import Candidatura, Municipio

    session.add(
        Municipio(ibge="4306304", nome="Doutor Ricardo", uf="RS", nome_chave="DOUTOR RICARDO")
    )
    session.flush()
    for i, (nome, situacao) in enumerate(
        [
            ("Alberto de Mozzi", "ELEITO POR QP"),
            ("Volmir Luis Gomes", "ELEITO POR MEDIA"),
            ("Edecasio Boiani", "SUPLENTE"),
        ]
    ):
        session.add(
            Candidatura(
                sq_candidato=f"sq{i}", ano_eleicao=2024, uf="RS", unidade="Doutor Ricardo", municipio_ibge="4306304",
                cargo="VEREADOR", nome=nome, nome_urna=nome, situacao_turno=situacao,
            )
        )  # fmt: skip
    session.flush()
    achados = fc.vereadores_icamaras(_ler("icamaras_vereadores.html"), "")
    assert fc.confirmar_pelo_tse(session, "4306304", achados) == 2
    exercicio = {v["nome"] for v in achados if v["em_exercicio"]}
    assert exercicio == {"Alberto de Mozzi", "Volmir Luis Gomes"}  # o suplente do TSE não entra


def test_portalfacil_junta_o_partido_da_aba_de_partidos():
    achados = {
        v["id_externo"]: v
        for v in fc.vereadores_portalfacil(_ler("portalfacil_parlamentares.html"), "")
    }
    assert achados["19"]["nome"] == "Ana Ávila" and achados["19"]["partido"] == "AVANTE"
    assert achados["18"]["partido"] is None  # só apareceu na aba sem partido
    assert achados["2"]["partido"] == "MDB"


def test_portalfacil_acha_a_lista_da_legislatura_na_capa():
    links = fc.links_portalfacil(_ler("portalfacil_capa.html"), "https://capimbranco.mg.leg.br/")
    assert links == ["https://www.capimbranco.mg.leg.br/parlamentares/legislatura/18-2025-2028/3"]


def test_ingadigital_le_so_a_legislatura_atual_e_sem_partido():
    capa = _ler("ingadigital_capa.html")
    assert fc.link_vereadores_inga(capa, "https://cmitambe.pr.gov.br/").endswith(
        "sessao=b054603368x0b0"
    )
    achados = fc.vereadores_inga(_ler("ingadigital_vereadores.html"), "")
    assert len(achados) == 9
    assert achados[0]["nome"] == "Andre Luiz Vertuan dos Santos"
    assert all(v["partido"] is None for v in achados)  # o site não publica partido


def test_cespro_lista_tira_menu_repetido_e_pega_a_sigla_do_nome():
    itens = fc.links_cespro(_ler("cespro_lista.html"))
    assert [i[0] for i in itens] == ["1619", "1103", "1613", "1615", "1618"]
    assert fc.sigla_do_menu(itens[0][2]) == "PDT"
    assert fc.nome_e_partido(itens[0][2])[0] == "Cinésio Francisco Angst"


def test_cespro_lista_ignora_comissoes_e_bancadas():
    pagina = (
        '<a href="/site/vereadores/1-">Comissão Permanente Única PARA 2026</a>'
        '<a href="/site/vereadores/2-">Rejane Alice Weiler (PP)</a>'
    )
    assert [i[0] for i in fc.links_cespro(pagina)] == ["2"]


def test_cespro_ficha_traz_nome_civil_e_partido_sem_data_de_nascimento():
    assert fc.ficha_cespro(_ler("cespro_ficha.html")) == ("Clodoaldo Silva dos Santos", "PP")


@respx.mock
def test_coletar_webservices_pela_api_json(monkeypatch):
    monkeypatch.setattr(fc, "PAUSA", 0)
    respx.get("https://cmexemplo.ma.gov.br/robots.txt").mock(return_value=httpx.Response(404))
    corpo = json.loads(_ler("webservicesistemas_vereadores.json"))[:4]
    corpo = [dict(corpo[i % 4], id=900 + i) for i in range(9)]
    respx.get("https://cmexemplo.ma.gov.br/api/vereadores").mock(
        return_value=httpx.Response(200, json=corpo)
    )
    camara = fc.coletar("https://cmexemplo.ma.gov.br/", "webservicesistemas")
    assert len(camara["vereadores"]) == 9
    assert camara["base"].endswith("/api/vereadores")


@respx.mock
def test_coletar_nao_segue_redirecionamento_para_outro_site(monkeypatch):
    monkeypatch.setattr(fc, "PAUSA", 0)
    respx.get("https://cmexemplo.pr.gov.br/robots.txt").mock(return_value=httpx.Response(404))
    respx.get("https://cmexemplo.pr.gov.br/").mock(
        return_value=httpx.Response(302, headers={"location": "https://play-buyers.com/"})
    )
    respx.get("https://play-buyers.com/").mock(
        return_value=httpx.Response(200, text="<html></html>")
    )
    with pytest.raises(ValueError, match="outro site"):
        fc.coletar("https://cmexemplo.pr.gov.br/", "ingadigital")


@respx.mock
def test_coletar_respeita_o_robots_txt(monkeypatch):
    monkeypatch.setattr(fc, "PAUSA", 0)
    respx.get("https://cmexemplo.ma.gov.br/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /")
    )
    with pytest.raises(PermissionError):
        fc.coletar("https://cmexemplo.ma.gov.br/", "webservicesistemas")


def test_fonte_citada_no_site_e_a_deste_conector():
    from app.services.camaras import _fonte

    enderecos = [
        "https://cmbernardodomearim.ma.gov.br/api/vereadores",
        "https://alegretedopiaui.pi.leg.br/alegretedopiaui/acessoinformacao/parlamentares",
        "https://camarabossoroca.rs.gov.br/site/vereadores",
        "https://herval.rs.leg.br/vereadores",
        "https://www.capimbranco.mg.leg.br/parlamentares/legislatura/18-2025-2028/3",
        "https://www.cmchale.mg.gov.br/parlamentares",
        "https://www.cmitambe.pr.gov.br//index.php?sessao=b054603368x0b0",
    ]
    for url in enderecos:
        assert _fonte("camara", "XX", url)[0] == "fornecedores_cobertura_camaras", url


def test_aplicar_descoberta_monta_camara_sapl_e_sistema_legislativo():
    from ingestion.canais.aplicar_descoberta import linhas_novas

    def cidade(ibge, nome, url, sistema, situacao):
        return {
            "ibge": ibge, "uf": "MA", "cidade": nome, "url": url,
            "sistema": sistema, "situacao": situacao, "evidencia": "",
        }  # fmt: skip

    novas = linhas_novas(
        [
            cidade("1", "Morros", "https://cmmorros.ma.gov.br/", "webservicesistemas", "aberto"),
            cidade("2", "Rio Largo", "https://sapl.riolargo.al.leg.br/", "sapl", "aberto"),
            cidade("3", "Outra", "https://camaraoutra.ma.gov.br/", "wordpress", "desconhecido"),
            cidade("4", "Sem Site", "", "", "desconhecido"),
            # domínio fraco e página que veda robôs: sem prova de que é da cidade
            cidade("5", "Fraca", "https://cmfraca.com.br/", "", "bloqueado"),
        ],
        "2026-10-27",
    )
    tipos = [(n["ibge"], n["tipo"], n["sistema"]) for n in novas]
    assert tipos == [
        ("1", "camara", ""),
        ("1", "sistema_legislativo", "webservicesistemas"),
        ("2", "camara", ""),
        ("2", "sapl", "sapl"),
        ("3", "camara", ""),
    ]
