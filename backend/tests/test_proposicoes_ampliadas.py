"""Proposições ampliadas: autor que não é parlamentar e proposições votadas fora do recorte.

Fixtures reais recortadas: `camara_autores_misto.csv` (arquivo de autores de 2025),
`camara_proposicao_votada_ficha.json` (PL 8889/2017) e `senado_processos_geral_votadas.json`
(lista geral de processos e fichas por `codigoMateria`)."""

import json
from datetime import date
from pathlib import Path

import httpx
import respx
from sqlalchemy import select

from app.models import Proposicao, Votacao
from ingestion import proposicoes_comum as pc
from ingestion.camara import proposicoes as camara
from ingestion.senado import proposicoes as senado
from tests.test_api import _ingestao, _popular

FIXTURES = Path(__file__).parent / "fixtures"
AUTORES = (FIXTURES / "camara_autores_misto.csv").read_bytes()
FICHA = json.loads((FIXTURES / "camara_proposicao_votada_ficha.json").read_text(encoding="utf-8"))
SENADO = json.loads((FIXTURES / "senado_processos_geral_votadas.json").read_text(encoding="utf-8"))
BASE = {"ementa": "E.", "situacao": None, "virou_lei": False, "url": "u", "ano": 2025}


def _proposicao(id_externo, **extra):
    return {
        **BASE,
        "id_externo": id_externo,
        "sigla_tipo": "PL",
        "numero": 1,
        "data_apresentacao": date(2025, 1, 10),
        **extra,
    }


def _votacao(session, casa, id_externo, proposicao_id):
    session.add(
        Votacao(
            casa=casa,
            id_externo=id_externo,
            data=date(2025, 6, 1),
            descricao="d",
            proposicao_id_externo=proposicao_id,
        )
    )
    session.flush()


def test_autores_que_nao_sao_deputados_viram_descricao():
    descricoes = camara.normalizar_autores_externos(AUTORES)
    assert descricoes == {
        "2622472": "Poder Executivo",
        "2599331": "Comissão de Desenvolvimento Urbano",
        "2646600": "Senado Federal - Rogério Carvalho",
    }
    # 2598919 (dois registros do mesmo deputado) e 2598952 (deputado e senador) têm deputado.
    assert "2598919" not in descricoes and "2598952" not in descricoes


def test_carregar_autores_grava_descricao_e_limpa_quem_ganhou_deputado(session):
    ingestao = _ingestao(session)
    pc.upsert_proposicoes(
        session,
        "camara",
        [
            _proposicao("2622472", origem="legislatura"),
            _proposicao("2599331", origem="legislatura"),
            _proposicao("2598919", origem="legislatura", autor_descricao="Poder Executivo"),
        ],
        ingestao,
    )
    camara.carregar_autores(session, AUTORES, ingestao)
    camara.carregar_autores(session, AUTORES, ingestao)  # idempotente
    session.expire_all()
    descricao = {p.id_externo: p.autor_descricao for p in session.scalars(select(Proposicao)).all()}
    assert descricao == {
        "2622472": "Poder Executivo",
        "2599331": "Comissão de Desenvolvimento Urbano",
        "2598919": None,  # o arquivo agora mostra deputado autor
    }


def test_proposicoes_da_legislatura_ganham_origem():
    conteudo = (
        '﻿"id";"siglaTipo";"numero";"ano";"ementa";"dataApresentacao";'
        '"ultimoStatus_descricaoSituacao"\n'
        '"1";"PL";"10";"2023";"Cria algo.";"2023-03-01T10:00:00";""\n'
    ).encode()
    assert camara.normalizar_proposicoes(conteudo)[0]["origem"] == "legislatura"


def test_ficha_da_camara_vira_proposicao_votada():
    registro = camara.normalizar_ficha(FICHA["dados"])
    assert registro["id_externo"] == "2157806"
    assert (registro["sigla_tipo"], registro["numero"], registro["ano"]) == ("PL", 8889, 2017)
    assert registro["data_apresentacao"] == date(2017, 10, 18)
    assert registro["situacao"] == "Aguardando Apreciação pelo Senado Federal"
    assert registro["virou_lei"] is False
    assert registro["url"].endswith("idProposicao=2157806")
    assert camara.normalizar_ficha({**FICHA["dados"], "dataApresentacao": None}) is None


def test_votadas_da_camara_so_as_que_faltam_e_sem_mexer_nas_existentes(session):
    ingestao = _ingestao(session)
    existente = pc.upsert_proposicoes(
        session,
        "camara",
        [_proposicao("2500000", origem="legislatura", autor_descricao="Poder Executivo")],
        ingestao,
    )
    _votacao(session, "camara", "v1", "2157806")  # antiga: falta
    _votacao(session, "camara", "v2", "2500000")  # já está na tabela
    _votacao(session, "camara", "v3", None)
    _votacao(session, "senado", "v4", "999")  # outra casa não conta
    assert pc.ids_votados_faltantes(session, "camara") == ["2157806"]

    payload = {"2157806": FICHA["dados"]}
    assert camara.carregar_votadas(session, payload, ingestao) == 1
    assert camara.carregar_votadas(session, payload, ingestao) == 1  # idempotente
    session.expire_all()
    votada = session.scalars(select(Proposicao).where(Proposicao.id_externo == "2157806")).one()
    assert (votada.origem, votada.ano, votada.autor_descricao) == ("votada", 2017, None)
    assert pc.ids_votados_faltantes(session, "camara") == []
    assert session.get(Proposicao, existente["2500000"]).origem == "legislatura"
    # Sem fichas (nada faltava) a carga não falha.
    assert camara.carregar_votadas(session, {}, ingestao) == 0


@respx.mock
def test_baixar_fichas_pula_404(monkeypatch):
    monkeypatch.setattr(camara, "PAUSA", 0)
    respx.get(camara.URL_FICHA.format(id="2157806")).mock(
        return_value=httpx.Response(200, json=FICHA)
    )
    respx.get(camara.URL_FICHA.format(id="1")).mock(return_value=httpx.Response(404))
    with httpx.Client() as client:
        fichas = camara.baixar_fichas(client, ["2157806", "1"])
    assert list(fichas) == ["2157806"]


def test_senado_lista_geral_traz_so_o_que_a_carga_por_senador_nao_trouxe():
    geral = senado.normalizar_geral(SENADO["geral"], ja_tem={"155732"})
    # PL 74/2023 foi apresentado em 27/12/2022: fora da legislatura.
    assert {(r["id_externo"], r["autor_descricao"]) for r in geral} == {
        ("156347", "Câmara dos Deputados"),
        ("166490", "Comissão de Segurança Pública"),
    }
    assert all(r["origem"] == "legislatura" for r in geral)
    assert senado.normalizar_geral(SENADO["geral"], ja_tem={"156347", "166490"}) == []


def test_senado_votadas_aceitam_mpv_e_qualquer_ano():
    votadas = {r["id_externo"]: r for r in senado.normalizar_votadas(SENADO["votadas"])}
    assert votadas["166971"]["sigla_tipo"] == "MPV"
    assert votadas["166971"]["autor_descricao"] == "Presidência da República"
    assert votadas["168484"]["sigla_tipo"] == "PEC"
    assert "origem" not in votadas["166971"]  # a origem é posta na gravação


def test_senado_carregar_grava_autoria_geral_e_votadas(session):
    _, senadores = _popular(session)
    codigo = senadores[0]["id_externo"]
    processo = {
        "identificacao": "PL 2036/2023", "casaIdentificadora": "SF", "codigoMateria": 157013,
        "dataApresentacao": "2023-04-19", "ementa": "Estabelece normas.",
        "situacaoAtual": "AGUARDANDO DESIGNAÇÃO DO RELATOR",
        "autoria": "Senador Fulano (PL/RJ)",
    }  # fmt: skip
    payload = {
        codigo: [processo],
        senado.CHAVE_GERAL: SENADO["geral"] + [processo],  # a mesma matéria nas duas listas
        senado.CHAVE_VOTADAS: SENADO["votadas"],
    }
    ingestao = _ingestao(session)
    senado.carregar(session, payload, ingestao)
    senado.carregar(session, payload, ingestao)  # idempotente
    session.expire_all()
    linhas = {p.id_externo: p for p in session.scalars(select(Proposicao)).all()}
    assert set(linhas) == {"157013", "156347", "166490", "166971", "168484"}
    assert linhas["157013"].origem == "legislatura" and linhas["157013"].autor_descricao is None
    assert linhas["156347"].autor_descricao == "Câmara dos Deputados"
    assert (linhas["166971"].origem, linhas["168484"].origem) == ("votada", "votada")

    # Quem era "votada" e entra na legislatura passa a ser "legislatura"; o inverso nunca.
    payload[senado.CHAVE_GERAL] = SENADO["geral"] + [
        {**SENADO["votadas"][1], "autoria": "Comissão de Teste"}
    ]
    senado.carregar(session, payload, ingestao)
    session.expire_all()
    pec = session.scalars(select(Proposicao).where(Proposicao.id_externo == "168484")).one()
    assert (pec.origem, pec.autor_descricao) == ("legislatura", "Comissão de Teste")


def test_senado_carga_antiga_sem_chaves_novas_continua_valendo(session):
    _, senadores = _popular(session)
    processo = {
        "identificacao": "PL 2036/2023", "casaIdentificadora": "SF", "codigoMateria": 157013,
        "dataApresentacao": "2023-04-19", "ementa": "E.", "situacaoAtual": "X",
        "autoria": "Senador Fulano (PL/RJ)",
    }  # fmt: skip
    assert (
        senado.carregar(session, {senadores[0]["id_externo"]: [processo]}, _ingestao(session)) == 1
    )


@respx.mock
def test_senado_baixar_pede_lista_geral_e_ficha_das_votadas(monkeypatch):
    monkeypatch.setattr(senado, "PAUSA", 0)
    pedidos = []

    def responder(request):
        params = dict(request.url.params)
        pedidos.append(params)
        if params.get("codigoMateria") == "166971":
            return httpx.Response(200, json=SENADO["votadas"][:1])
        if params.get("sigla") == "PL" and params.get("ano") == "2024":
            return httpx.Response(200, json=SENADO["geral"][:2])
        return httpx.Response(200, json=[])

    respx.get(senado.URL).mock(side_effect=responder)
    with httpx.Client() as client:
        payload = senado.baixar(client, ["5672"], ["166971"])
    anos = date.today().year - pc.INICIO_LEGISLATURA.year + 1
    assert len(pedidos) == 1 + len(pc.TIPOS) * anos + 1  # senador + sigla x ano + votada
    assert payload["5672"] == []
    assert len(payload[senado.CHAVE_GERAL]) == 2
    assert [p["codigoMateria"] for p in payload[senado.CHAVE_VOTADAS]] == [166971]


def test_tipos_da_legislatura_nao_mudam():
    # As siglas votadas (MPV, PLV...) entram só como "votada"; o recorte da legislatura fica.
    assert pc.TIPOS == {"PL", "PLP", "PEC", "PDL"}
