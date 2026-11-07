"""Projetos que viraram lei: normalização (amostra real do Senado), carga, ligação com os
projetos e as três rotas (filtro de /projetos, detalhe do projeto e perfil).

Conferido na fonte: Lei Complementar 214, de 16/01/2025 (DOU extra do mesmo dia), veio do PLP
68/2024 (Câmara id 2430143; Senado codigoMateria 164914). Lei 14.133, de 01/04/2021, veio do PLS
559/2013 (Senado 115926), que voltou ao Senado como PL 4253/2020 (substitutivo da Câmara)."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.models import Autoria, FonteIngestao, Norma, NormaProposicao, Tramitacao
from ingestion.congresso import normas
from tests import helpers_projetos as h
from tests.conftest import carregar_fixture


@pytest.fixture
def amostra():
    return carregar_fixture("normas_amostra.json")


def _ingestao(session):
    ing = FonteIngestao(
        fonte=normas.FONTE, url="x", arquivo_raw="x", status="ok",
        concluido_em=datetime(2026, 11, 7, 12, tzinfo=UTC),
    )  # fmt: skip
    session.add(ing)
    session.flush()
    return ing


def _norma(session, tipo, numero, ano):
    return session.scalars(
        select(Norma).where(Norma.tipo == tipo, Norma.numero == numero, Norma.ano == ano)
    ).one()


def test_normalizar_normas_le_objeto_ano_vazio_e_ec_repetida(amostra):
    linhas = normas.normalizar_normas(amostra)
    chaves = {(r["tipo"], r["numero"], r["ano"]): r for r in linhas}
    # LCP 2025 veio como objeto (uma norma só); EMC 2021 sem "documentos".
    assert set(chaves) == {
        ("LEI", 14133, 2021), ("LEI", 15270, 2025), ("LEI", 15100, 2025),
        ("LCP", 214, 2025), ("EMC", 25, 1985), ("EMC", 132, 2023),
    }  # fmt: skip
    lc = chaves[("LCP", 214, 2025)]
    assert lc["data"] == date(2025, 1, 16)
    assert lc["id_externo"] == "40180341"
    assert lc["ementa"].startswith("Institui o Imposto sobre Bens e Serviços (IBS)")
    assert lc["url"] == (
        "https://normas.leg.br/?urn=urn:lex:br:federal:lei.complementar:2025-01-16;214"
    )
    assert chaves[("LEI", 14133, 2021)]["data"] == date(2021, 4, 1)
    assert chaves[("LEI", 14133, 2021)]["url"].endswith("federal:lei:2021-04-01;14133")
    assert chaves[("EMC", 132, 2023)]["url"].endswith("emenda.constitucional:2023-12-20;132")


def test_norma_gerada_e_identificacao():
    assert normas.norma_gerada("Lei Complementar nº 214 de 16/01/2025") == (
        "LCP", 214, date(2025, 1, 16),
    )  # fmt: skip
    assert normas.norma_gerada("Lei nº 15.240 de 28/10/2025") == ("LEI", 15240, date(2025, 10, 28))
    assert normas.norma_gerada("Emenda Constitucional nº 132 de 20/12/2023")[0] == "EMC"
    assert normas.norma_gerada("Decreto Legislativo nº 1 de 01/01/2025") is None
    assert normas.identificacao("PL 4253/2020 (Substitutivo-CD)") == ("PL", 4253, 2020)
    assert normas.identificacao("PLP 00068/2024") == ("PLP", 68, 2024)


def test_normalizar_processos_deixa_veto_de_fora(amostra):
    processos = normas.normalizar_processos(amostra)
    idents = {p["identificacao"] for p in processos}
    assert "PLS 559/2013" in idents and "PLP 68/2024" in idents and "PEC 45/2019" in idents
    assert not any(i.startswith("VET") for i in idents)  # veto não é o projeto de origem
    plp = next(p for p in processos if p["identificacao"] == "PLP 68/2024")
    assert plp["codigo"] == "164914" and plp["revisora"] is True
    assert plp["norma"] == ("LCP", 214, date(2025, 1, 16))


def test_transformado_em_le_o_despacho_da_camara():
    t = normas.transformado_em
    assert t(
        "Transformado na Lei Complementar 214/2025. DOU 16/01/2025 PÁG 01 COL 01 - Ed.  Extra B."
    ) == ("LCP", 214, 2025, date(2025, 1, 16))
    assert t("Transformado na Lei Ordinária 15123/2025. DOU 25/04/2025 PÁG 03 COL 01.") == (
        "LEI", 15123, 2025, date(2025, 4, 25),
    )  # fmt: skip
    assert t("Transformado na Lei 15300/2025. DOU 23/12/2025 PÁG 01.")[:3] == ("LEI", 15300, 2025)
    assert t("Transformado na Emenda Constitucional 132/2023.") == ("EMC", 132, 2023, None)
    assert t("Transformado no Decreto Legislativo 80/2026. DOU 10 06 2026 PÁG 02.") is None


def _carregar(session, amostra):
    ing = _ingestao(session)
    normas.carregar(session, amostra, ing)
    session.flush()
    return ing


def test_carga_liga_a_lc_214_ao_plp_68_nas_duas_casas(session, amostra):
    camara = h.proposicao(session, "2430143", sigla="PLP", numero=68, ano=2024)
    session.add(
        Tramitacao(
            casa="camara", proposicao_id_externo=camara.id_externo, ordem=1,
            data=datetime(2025, 1, 16), descricao=(
                "Transformado na Lei Complementar 214/2025. DOU 16/01/2025 PÁG 01 COL 01."
            ),
        )
    )  # fmt: skip
    session.flush()
    _carregar(session, amostra)

    lc = _norma(session, "LCP", 214, 2025)
    assert lc.data == date(2025, 1, 16) and lc.data_publicacao == date(2025, 1, 16)
    ligacoes = {
        (r.casa, r.proposicao_id_externo, r.identificacao, r.origem)
        for r in session.scalars(select(NormaProposicao).where(NormaProposicao.norma_id == lc.id))
    }
    # A ligação pelo número (numeração única) vem antes da do despacho: fica uma só.
    assert ligacoes == {
        ("senado", "164914", "PLP 68/2024", "senado"),
        ("camara", "2430143", "PLP 68/2024", "numero"),
    }
    lei = _norma(session, "LEI", 14133, 2021)
    origens = set(
        session.scalars(
            select(NormaProposicao.identificacao).where(NormaProposicao.norma_id == lei.id)
        )
    )
    assert origens == {"PLS 559/2013", "PL 4253/2020 (Substitutivo-CD)"}


def test_pec_so_liga_na_camara_quando_o_senado_foi_revisor(session, amostra):
    h.proposicao(session, "2196833", sigla="PEC", numero=45, ano=2019)
    _carregar(session, amostra)
    ec = _norma(session, "EMC", 132, 2023)
    casas = set(
        session.scalars(select(NormaProposicao.casa).where(NormaProposicao.norma_id == ec.id))
    )
    assert casas == {"senado", "camara"}


def test_carga_e_idempotente_e_aborta_sem_normas(session, amostra):
    _carregar(session, amostra)
    _carregar(session, amostra)
    assert session.scalar(select(func.count()).select_from(Norma)) == 6
    ligacoes = session.scalar(select(func.count()).select_from(NormaProposicao))
    assert ligacoes == 6  # PLS 559, PL 4253, PL 1087, PL 4932, PLP 68, PEC 45 (sem vetos)
    with pytest.raises(RuntimeError):
        normas.carregar(
            session, {"anos": [2025], "normas": {}, "processos": []}, _ingestao(session)
        )


def test_filtro_virou_lei_conta_por_ano_e_abre_um_ano(client, session, amostra):
    h.proposicao(session, "2430143", sigla="PLP", numero=68, ano=2024)
    _carregar(session, amostra)
    r = client.get("/projetos", params={"virou_lei": "sim"}).json()
    leis = r["leis"]
    assert r["total"] == 6 and r["itens"] == []
    assert [a["ano"] for a in leis["anos"]] == [2025, 2023, 2021, 1985]
    assert leis["anos"][0] == {
        "ano": 2025, "total": 3, "leis": 2, "leis_complementares": 1,
        "emendas_constitucionais": 0,
    }  # fmt: skip
    assert leis["itens"] == [] and leis["ano"] is None  # os anos começam fechados
    assert leis["atualizado_em"] is not None

    r = client.get("/projetos", params={"virou_lei": "sim", "ano_lei": 2025}).json()
    itens = r["leis"]["itens"]
    assert [i["nome"] for i in itens] == [
        "Lei 15.270/2025", "Lei Complementar 214/2025", "Lei 15.100/2025",
    ]  # fmt: skip
    lc = itens[1]
    assert lc["nome_oficial"] == "Lei Complementar nº 214, de 16 de janeiro de 2025"
    assert {"casa": "camara", "id_externo": "2430143", "identificacao": "PLP 68/2024",
            "link": "/projeto/camara/2430143"} in lc["projetos"]  # fmt: skip

    r = client.get(
        "/projetos", params={"virou_lei": "sim", "q": "Lei 14.133/2021", "ano_lei": 2021}
    )
    assert [i["nome_oficial"] for i in r.json()["leis"]["itens"]] == [
        "Lei nº 14.133, de 1º de abril de 2021"
    ]
    r = client.get("/projetos", params={"virou_lei": "sim", "q": "imposto seletivo"}).json()
    assert r["total"] == 1


def test_detalhe_do_projeto_traz_a_lei(client, session, amostra):
    h.proposicao(session, "2430143", sigla="PLP", numero=68, ano=2024)
    _carregar(session, amostra)
    norma = client.get("/projetos/camara/2430143").json()["norma"]
    assert norma["nome"] == "Lei Complementar 214/2025"
    assert norma["data"] == "2025-01-16"
    assert norma["url"].endswith("lei.complementar:2025-01-16;214")
    assert norma["fonte_url"].startswith("https://legis.senado.leg.br")
    h.proposicao(session, "999", sigla="PL", numero=9, ano=2025)
    assert client.get("/projetos/camara/999").json()["norma"] is None


def test_perfil_viraram_lei_com_media_da_casa(client, session, amostra):
    autora = h.parlamentar(session, "Fulana", "SP", "XX")
    outro = h.parlamentar(session, "Beltrano", "RJ", "YY")
    h.parlamentar(session, "Sicrano", "MG", "ZZ")
    plp = h.proposicao(session, "2430143", sigla="PLP", numero=68, ano=2024)
    pl = h.proposicao(session, "2487436", sigla="PL", numero=1087, ano=2025)
    sem_lei = h.proposicao(session, "1", sigla="PL", numero=1, ano=2025)
    session.add_all(
        [
            Autoria(proposicao_id=plp.id, parlamentar_id=autora.id, primeiro_autor=False),
            Autoria(proposicao_id=pl.id, parlamentar_id=autora.id, primeiro_autor=True),
            Autoria(proposicao_id=sem_lei.id, parlamentar_id=autora.id, primeiro_autor=True),
            Autoria(proposicao_id=pl.id, parlamentar_id=outro.id, primeiro_autor=False),
        ]
    )
    session.flush()
    _carregar(session, amostra)
    r = client.get(f"/parlamentares/{autora.id}/projetos").json()["viraram_lei"]
    assert r["total"] == 2 and r["primeiro_autor"] == 1
    assert r["media_casa"] == 1.0  # (2 + 1 + 0) / 3 em exercício
    assert [(i["projeto"], i["norma"]["nome"]) for i in r["itens"]] == [
        ("PL 1087/2025", "Lei 15.270/2025"),
        ("PLP 68/2024", "Lei Complementar 214/2025"),
    ]
