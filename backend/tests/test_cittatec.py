# ruff: noqa: E501  (recortes de respostas reais da API da Cittatec)
import json
from datetime import date
from pathlib import Path

import respx

from app.models import Candidatura, Municipio
from ingestion.camaras import cittatec, sapl
from ingestion.canais import catalogo
from ingestion.canais import varredura as v
from tests.test_api import _ingestao

# Barra do Ribeiro (RS), legislatura 2025-2028: titulares, uma substituição e um suplente que
# assumiu (fotos e biografias retiradas do recorte).
REGISTROS = json.loads(
    (Path(__file__).parent / "fixtures" / "cittatec_parlamentares.json").read_text(encoding="utf-8")
)
LEGISLATURAS = [
    {"id": 3, "nome": "LEGISLATURA", "dataInicio": "2025-01-01", "dataFim": "2028-12-31", "legislaturaAtual": True, "anoInicial": 2025, "anoFinal": 2028},
    {"id": 1, "nome": "Legislatura", "dataInicio": "2021-01-01", "dataFim": "2024-12-31", "legislaturaAtual": False, "anoInicial": 2021, "anoFinal": 2024},
]  # fmt: skip
PROPOSICOES = [
    {"idProposicao": 10, "nomeProposicao": "REQUERIMENTO", "quantidade": 31},
    {"idProposicao": 25, "nomeProposicao": "PROJETO DE LEI ORDINÁRIA", "quantidade": 25},
    {"idProposicao": 33, "nomeProposicao": "PEDIDO DE PROVIDÊNCIAS", "quantidade": 12},
    {"idProposicao": 44, "nomeProposicao": "JUSTIFICATIVA DE AUSÊNCIA", "quantidade": 1},
    {"idProposicao": 52, "nomeProposicao": "PARECER", "quantidade": 24},
    {"idProposicao": 59, "nomeProposicao": "MEMORANDO", "quantidade": 56},
]  # fmt: skip


def test_tenant_do_endereco():
    assert (
        cittatec.tenant_de("https://cmpelotas.cittatec.com.br/portal-legislativo/vereadores")
        == "cmpelotas"
    )
    assert cittatec.tenant_de("https://www.pelotas.rs.leg.br/") is None


def test_legislatura_atual_so_a_marcada_e_em_vigor():
    assert cittatec.legislatura_atual(LEGISLATURAS, date(2026, 10, 9))["id"] == 3
    # Marcada como atual mas encerrada há mais de 90 dias: o cadastro está parado.
    assert cittatec.legislatura_atual(LEGISLATURAS[:1], date(2029, 6, 1)) is None
    assert cittatec.legislatura_atual(LEGISLATURAS[1:], date(2026, 10, 9)) is None


def test_vereadores_um_por_pessoa_e_situacao():
    lista = {x["nome"]: x for x in cittatec.vereadores(REGISTROS)}
    assert len(lista) == 6
    patricia = lista["PATRICIA RAMOS"]
    assert (patricia["partido"], patricia["em_exercicio"], patricia["titular"]) == (
        "PROGRESSISTAS",
        True,
        True,
    )
    assert patricia["inicio"] == "2026-03-16" and patricia["fim"] == "2028-12-31"
    # Quem saiu depois de uma substituição não está em exercício e não é titular.
    roseli = lista["ROSELI NUNES DE SOUZA"]
    assert (roseli["em_exercicio"], roseli["titular"]) == (False, False)
    assert patricia["foto_url"] is None  # o endereço da foto embute o CPF


def test_mesma_pessoa_em_dois_periodos_vira_um_vereador():
    dois = [
        REGISTROS[1],
        {**REGISTROS[1], "id": 999, "ativo": False, "dataInicio": "2025-01-01T00:00:00"},
    ]
    [um] = cittatec.vereadores(dois)
    assert (um["em_exercicio"], um["inicio"]) == (True, "2025-01-01")


def test_contagem_ignora_o_que_nao_e_proposicao_de_autoria():
    assert cittatec.contagem_de_proposicoes(PROPOSICOES) == {
        "Requerimento": 31,
        "Projeto de lei ordinária": 25,
        "Pedido de providências": 12,
    }


@respx.mock
def test_coletar_e_gravar_liga_ao_eleito(monkeypatch, session):
    monkeypatch.setattr(cittatec, "PAUSA", 0)
    base = "https://cmbarradoribeiro.cittatec.com.br"
    respx.get(f"{base}/api/conecta/public/clientes/Y21iYXJyYWRvcmliZWlybw==/tenant").respond(
        json={"ID-Tenant": "cmbarradoribeiro"}
    )
    legislaturas = respx.get(f"{base}/api/open-data-leg/public/legislaturas").respond(
        json=LEGISLATURAS
    )
    respx.get(f"{base}/api/open-data-leg/public/parlamentares/legislaturas/3").respond(
        json=REGISTROS
    )
    props = respx.get(
        url__regex=rf"{base}/api/open-data-leg/public/mandatos/proposicoes/parlamentares/\d+"
    ).respond(json=PROPOSICOES)
    camara = cittatec.coletar(f"{base}/portal-legislativo/vereadores", date(2026, 10, 9))
    assert legislaturas.calls[0].request.headers["ID-Tenant"] == "cmbarradoribeiro"
    assert props.call_count == 6
    assert (
        props.calls[0].request.url.params["periodoMandato"]
        == "2025-01-01T00:00:00,2026-12-31T23:59:59"
    )
    assert camara["base"] == f"{base}/portal-legislativo/vereadores"

    session.add(
        Municipio(ibge="4301909", nome="Barra do Ribeiro", uf="RS", nome_chave="BARRA DO RIBEIRO")
    )
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="RS", unidade="Barra do Ribeiro",
                            municipio_ibge="4301909", nome="ANDREZA BUDELON", nome_urna="ANDREZA BUDELON",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    assert sapl.gravar(session, "4301909", camara) == 6
    from sqlalchemy import select

    from app.models import MandatoLocal

    mandatos = {m.nome: m for m in session.scalars(select(MandatoLocal))}
    assert mandatos["ANDREZA BUDELON"].candidatura_id is not None
    assert mandatos["PATRICIA RAMOS"].candidatura_id is None  # não foi eleita: não liga
    assert mandatos["PATRICIA RAMOS"].proposicoes_por_tipo["Requerimento"] == 31
    assert mandatos["PATRICIA RAMOS"].sapl_url.startswith(base)
    # Regravar não duplica.
    assert sapl.gravar(session, "4301909", camara) == 6
    assert len(list(session.scalars(select(MandatoLocal)))) == 6


@respx.mock
def test_coletar_sem_legislatura_em_vigor_devolve_nada(monkeypatch):
    monkeypatch.setattr(cittatec, "PAUSA", 0)
    base = "https://cmx.cittatec.com.br"
    respx.get(url__regex=rf"{base}/api/conecta/public/clientes/.*/tenant").respond(
        json={"ID-Tenant": "cmx"}
    )
    respx.get(f"{base}/api/open-data-leg/public/legislaturas").respond(json=LEGISLATURAS[1:])
    assert cittatec.coletar(f"{base}/portal-legislativo/vereadores", date(2026, 10, 9)) is None


def test_sapl_desativado_sai_do_catalogo(tmp_path):
    comum = {"municipio": "X", "uf": "RS", "sistema": "", "verificado_em": "2026-10-09"}
    varredura, curados, desativados = tmp_path / "v.csv", tmp_path / "c.csv", tmp_path / "d.csv"
    v.gravar_catalogo(
        [
            {**comum, "ibge": "4314407", "tipo": "sapl", "url": "https://sapl.pelotas.rs.leg.br/"},
            {**comum, "ibge": "4314407", "tipo": "camara", "url": "https://www.pelotas.rs.leg.br/"},
            {**comum, "ibge": "4300034", "tipo": "sapl", "url": "https://sapl.acegua.rs.leg.br/"},
        ],
        varredura,
    )
    v.gravar_catalogo([], curados)
    desativados.write_text(
        "ibge,municipio,uf,url_sapl,motivo,verificado_em\n4314407,Pelotas,RS,x,y,2026-10-09\n",
        encoding="utf-8",
    )
    resultado = {
        (c["municipio_ibge"], c["tipo"]) for c in catalogo.ler(varredura, curados, desativados)
    }
    assert resultado == {("4314407", "camara"), ("4300034", "sapl")}
    # O arquivo versionado de verdade lista câmaras que existem no catálogo.
    assert catalogo.SAPL_DESATIVADO.exists()
