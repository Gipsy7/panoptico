from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.api import argos as rotas
from app.config import settings
from app.models.argos import ArgosAvaliacao, ArgosConversa, ArgosFraseNaoEntendida
from app.services import argos as servico


@pytest.fixture(autouse=True)
def _zerar_limite():
    rotas._pedidos.clear()
    servico._ultima_limpeza = None


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("meu cep é 88340-000 e moro aqui", "meu cep é [removido] e moro aqui"),
        ("88340000", "[removido]"),
        ("cpf 123.456.789-09", "cpf [removido]"),
        ("cpf 12345678909", "cpf [removido]"),
        ("me liga (48) 99999-1234", "me liga [removido]"),
        ("fone 48999991234", "fone [removido]"),
        ("escreva para fulano@exemplo.com.br", "escreva para [removido]"),
        ("veja https://site.com/a?b=1 e www.x.com", "veja [removido] e [removido]"),
        ("protocolo 1234567", "protocolo [removido]"),
        ("deputados de SC em 2025", "deputados de SC em 2025"),
        ("  muitos    espaços  ", "muitos espaços"),
    ],
)
def test_limpar(entrada, esperado):
    assert servico.limpar(entrada) == esperado


def test_limpar_corta_no_limite():
    assert len(servico.limpar("a" * 900)) == servico.MAX_FRASE
    assert len(servico.limpar("b" * 900, servico.MAX_MENSAGEM)) == servico.MAX_MENSAGEM


def test_nao_entendida_grava_so_texto_limpo_e_dia(client, session):
    r = client.post("/argos/nao-entendida", json={"texto": "cep 88340-000 qual a lei do gato"})
    assert r.status_code == 204
    assert r.headers["cache-control"] == "no-store"
    linha = session.scalars(select(ArgosFraseNaoEntendida)).one()
    assert linha.texto == "cep [removido] qual a lei do gato"
    assert linha.dia == date.today()
    # Sem IP, user-agent nem sessão: a tabela só tem estas colunas.
    colunas = {c.name for c in ArgosFraseNaoEntendida.__table__.columns}
    assert colunas == {"id", "texto", "dia"}


def test_frase_so_com_dado_pessoal_nao_e_gravada(client, session):
    assert client.post("/argos/nao-entendida", json={"texto": "88340-000"}).status_code == 204
    assert session.scalars(select(ArgosFraseNaoEntendida)).all() == []


@pytest.mark.parametrize("corpo", [{"texto": ""}, {"texto": "x" * 301}, {}, {"texto": 5}])
def test_nao_entendida_valida_limites(client, corpo):
    assert client.post("/argos/nao-entendida", json=corpo).status_code == 422


def test_avaliacao_sem_conversa(client, session):
    r = client.post("/argos/avaliacao", json={"util": True, "assunto": "gastos"})
    assert r.status_code == 204
    a = session.scalars(select(ArgosAvaliacao)).one()
    assert (a.util, a.assunto, a.dia) == (True, "gastos", date.today())
    assert session.scalars(select(ArgosConversa)).all() == []


def test_avaliacao_com_conversa_consentida_limpa_o_texto(client, session):
    conversa = [
        {"autor": "cidadao", "texto": "moro no cep 01310-100"},
        {"autor": "argos", "texto": "x" * 800},
    ]
    r = client.post(
        "/argos/avaliacao", json={"util": False, "assunto": "representantes", "conversa": conversa}
    )
    assert r.status_code == 422  # 800 > 500: o limite vale no servidor
    conversa[1]["texto"] = "y" * 500
    r = client.post(
        "/argos/avaliacao", json={"util": False, "assunto": "representantes", "conversa": conversa}
    )
    assert r.status_code == 204
    c = session.scalars(select(ArgosConversa)).one()
    assert c.mensagens[0] == {"autor": "cidadao", "texto": "moro no cep [removido]"}
    assert len(c.mensagens) == 2


def test_conversa_limita_30_mensagens(client):
    conversa = [{"autor": "cidadao", "texto": "oi"}] * 31
    corpo = {"util": False, "assunto": "nenhum", "conversa": conversa}
    assert client.post("/argos/avaliacao", json=corpo).status_code == 422


@pytest.mark.parametrize(
    "corpo",
    [
        {"util": "talvez", "assunto": "gastos"},
        {"util": True, "assunto": "Gastos Do X"},
        {"util": True, "assunto": ""},
        {"util": True, "assunto": "a" * 41},
        {"util": True, "assunto": "gastos", "conversa": [{"autor": "ip", "texto": "x"}]},
    ],
)
def test_avaliacao_valida(client, corpo):
    assert client.post("/argos/avaliacao", json=corpo).status_code == 422


def test_nenhuma_rota_le_os_dados(client):
    for caminho in ("/argos", "/argos/nao-entendida", "/argos/avaliacao", "/argos/conversas"):
        assert client.get(caminho).status_code in (404, 405)
    rotas_get = {
        r.path
        for r in client.app.routes
        if "GET" in getattr(r, "methods", set()) and r.path.startswith("/argos")
    }
    assert rotas_get == set()


def test_registro_desligado_responde_204_e_nao_grava(client, session, monkeypatch):
    monkeypatch.setattr(settings, "argos_registro", False)
    assert client.post("/argos/nao-entendida", json={"texto": "uma frase"}).status_code == 204
    assert client.post("/argos/avaliacao", json={"util": True, "assunto": "x"}).status_code == 204
    assert session.scalars(select(ArgosFraseNaoEntendida)).all() == []
    assert session.scalars(select(ArgosAvaliacao)).all() == []


def test_limite_de_taxa_por_origem(client):
    corpo = {"texto": "uma frase qualquer"}
    for _ in range(rotas.LIMITE_POR_MINUTO):
        assert client.post("/argos/nao-entendida", json=corpo).status_code == 204
    assert client.post("/argos/nao-entendida", json=corpo).status_code == 429
    # Outra origem não é afetada.
    outra = client.post(
        "/argos/nao-entendida", json=corpo, headers={"cf-connecting-ip": "203.0.113.9"}
    )
    assert outra.status_code == 204


def test_apaga_o_que_passou_de_180_dias(session):
    velho = date.today() - timedelta(days=servico.DIAS_DE_GUARDA + 1)
    novo = date.today() - timedelta(days=10)
    session.add_all(
        [
            ArgosFraseNaoEntendida(texto="velha", dia=velho),
            ArgosFraseNaoEntendida(texto="nova", dia=novo),
            ArgosAvaliacao(util=True, assunto="x", dia=velho),
            ArgosConversa(mensagens=[], dia=velho),
        ]
    )
    session.flush()
    assert servico.apagar_antigos(session) == 3
    assert [f.texto for f in session.scalars(select(ArgosFraseNaoEntendida))] == ["nova"]


def test_cors_aceita_post_da_origem_configurada(client):
    r = client.options(
        "/argos/avaliacao",
        headers={
            "Origin": settings.cors_origins[0],
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert "POST" in r.headers["access-control-allow-methods"]
    assert r.headers["access-control-allow-origin"] == settings.cors_origins[0]
    # POST não é cacheado nem recebe "*".
    p = client.post(
        "/argos/avaliacao",
        json={"util": True, "assunto": "gastos"},
        headers={"Origin": settings.cors_origins[0]},
    )
    assert p.headers.get("access-control-allow-origin") != "*"
    assert p.headers["cache-control"] == "no-store"


def test_registros_do_argos_ficam_fora_da_exportacao_aberta():
    pasta = Path(__file__).resolve().parents[1] / "exportar"
    for arquivo in pasta.glob("*.py"):
        assert "argos" not in arquivo.read_text(encoding="utf-8").lower(), arquivo.name
