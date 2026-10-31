# ruff: noqa: E501
import json
import time
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api import metricas as rotas
from app.api import painel as rotas_painel
from app.config import settings
from app.models.metrica import MetricaDiaria
from app.services import metricas as servico
from app.services import painel_auth

NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/130 Mobile Safari/537.36"}
TEXTO = {**NAVEGADOR, "Content-Type": "text/plain;charset=UTF-8"}


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    rotas._pedidos.clear()
    rotas_painel._erros.clear()
    monkeypatch.setattr(settings, "metricas_ativas", True)
    monkeypatch.setattr(settings, "ambiente", "producao")
    monkeypatch.setattr(settings, "painel_usuario", "dono")
    monkeypatch.setattr(settings, "painel_senha_hash", painel_auth.gerar_hash("senha-muito-longa"))
    monkeypatch.setattr(settings, "painel_segredo", "segredo-de-teste")


def _visita(client, corpo, headers=TEXTO):
    return client.post("/metricas/visita", content=json.dumps(corpo), headers=headers)


def _totais(session):
    return {(m.tipo, m.chave): m.total for m in session.scalars(select(MetricaDiaria))}


NOVA = {
    "caminho": "/parlamentar/204554",
    "nova": True,
    "origem": "whatsapp",
    "dispositivo": "celular",
}


def test_visita_nova_conta_pagina_visita_origem_dispositivo(client, session):
    r = _visita(client, NOVA)
    assert r.status_code == 204
    assert r.headers["cache-control"] == "no-store"
    assert _totais(session) == {
        ("pagina", "/parlamentar/204554"): 1,
        ("visita", "total"): 1,
        ("origem", "whatsapp"): 1,
        ("dispositivo", "celular"): 1,
    }
    _visita(client, {"caminho": "/parlamentar/204554"})  # mesma visita, outra página vista
    totais = _totais(session)
    assert totais[("pagina", "/parlamentar/204554")] == 2
    assert totais[("visita", "total")] == 1


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("/", "/"),
        ("/representantes", "/representantes"),
        ("/representantes/", "/representantes"),
        ("/representantes?cep=01310100", None),
        ("/representantes#x", None),
        ("/representantes?uf=SC", None),
        ("/cep/01310100", None),
        ("/01310100", None),
        ("/parlamentar/204554", "/parlamentar/204554"),
        ("/parlamentar/01310100", None),
        ("/cidade/4205407", "/cidade/4205407"),
        ("/cidade/01310100", None),
        ("/partidos/pt", "/partidos/pt"),
        ("/eleito/12345678901", "/eleito/[id]"),
        ("/vereador/998877", "/vereador/[id]"),
        ("/projeto/camara/2345678", "/projeto/[id]"),
        ("/votacao/local/123456", "/votacao/[id]"),
        ("/impostos-e-repasses/sc/4205407", "/impostos-e-repasses/[lugar]"),
        ("/painel", None),
        ("/qualquer-coisa-inventada", None),
        ("/" + "a" * 200, None),
        ("https://x.com/", None),
        ("/com espaço", None),
        (None, None),
        (5, None),
    ],
)
def test_limpar_caminho(bruto, esperado):
    assert servico.limpar_caminho(bruto) == esperado


def test_caminho_com_cep_nao_grava(client, session):
    for caminho in ("/representantes?cep=01310100", "/eleito/01310100/x", "/01310-100"):
        assert _visita(client, {**NOVA, "caminho": caminho}).status_code == 204
    assert _totais(session) == {}


@pytest.mark.parametrize(
    "corpo",
    [
        {**NOVA, "origem": "texto livre"},
        {**NOVA, "dispositivo": "tablet"},
        {**NOVA, "origem": None},
        [1, 2],
        "texto",
    ],
)
def test_valores_fora_da_lista_sao_ignorados(client, session, corpo):
    assert _visita(client, corpo).status_code == 204
    assert _totais(session) == {}


def test_corpo_invalido_ou_grande_responde_204_sem_gravar(client, session):
    assert (
        client.post("/metricas/visita", content="isto nao e json", headers=TEXTO).status_code == 204
    )
    grande = json.dumps({**NOVA, "extra": "x" * 5000})
    assert client.post("/metricas/visita", content=grande, headers=TEXTO).status_code == 204
    assert _totais(session) == {}


@pytest.mark.parametrize(
    "ua", ["Googlebot/2.1", "meu-crawler", "Spider-X", "HeadlessChrome/120", ""]
)
def test_robo_nao_conta(client, session, ua):
    assert (
        _visita(client, NOVA, {"User-Agent": ua, "Content-Type": "text/plain"}).status_code == 204
    )
    assert _totais(session) == {}


def test_flag_desligada_nao_toca_no_banco(client, session, monkeypatch):
    monkeypatch.setattr(settings, "metricas_ativas", False)
    assert _visita(client, NOVA).status_code == 204
    assert (
        client.post("/metricas/recurso", content='{"recurso":"cep"}', headers=TEXTO).status_code
        == 204
    )
    assert _totais(session) == {}


@pytest.mark.parametrize("ambiente", ["release", "desenvolvimento", ""])
def test_fora_da_producao_nao_grava(client, session, monkeypatch, ambiente):
    monkeypatch.setattr(settings, "ambiente", ambiente)
    assert _visita(client, NOVA).status_code == 204
    assert _totais(session) == {}


def test_origem_de_outro_site_e_ignorada(client, session):
    _visita(client, NOVA, {**TEXTO, "Origin": "https://outro-site.example"})
    assert _totais(session) == {}
    _visita(client, NOVA, {**TEXTO, "Origin": settings.cors_origins[0]})
    assert _totais(session)[("visita", "total")] == 1


def test_recurso_so_aceita_a_lista(client, session):
    for r in ("cep", "pix", "texto-livre", 7, None):
        client.post("/metricas/recurso", content=json.dumps({"recurso": r}), headers=TEXTO)
    assert _totais(session) == {("recurso", "cep"): 1, ("recurso", "pix"): 1}


def test_limite_por_ip_em_memoria(client, session, monkeypatch):
    monkeypatch.setattr(rotas, "LIMITE_POR_MINUTO", 3)
    for _ in range(6):
        _visita(client, {"caminho": "/"}, {**TEXTO, "CF-Connecting-IP": "203.0.113.9"})
    assert _totais(session)[("pagina", "/")] == 3


def test_metricas_sem_cors_aberto_e_sem_cache(client):
    r = _visita(client, NOVA, {**TEXTO, "Origin": "http://localhost:3000"})
    assert r.headers["cache-control"] == "no-store"
    assert r.headers.get("access-control-allow-origin") != "*"
    r = client.post(
        "/metricas/visita", headers={"Content-Type": "text/plain"}
    )  # sem user-agent útil
    assert r.headers["cache-control"] == "no-store"


# ---------- painel ----------


def _entrar(client, usuario="dono", senha="senha-muito-longa", **kw):
    return client.post("/painel/entrar", json={"usuario": usuario, "senha": senha}, **kw)


def _auth(client):
    token = _entrar(client).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_senha_certa_devolve_token_e_resumo(client, session):
    _visita(client, NOVA)
    _visita(client, {"caminho": "/", "nova": True, "origem": "direto", "dispositivo": "computador"})
    client.post("/metricas/recurso", content='{"recurso":"cep"}', headers=TEXTO)
    r = client.get("/painel/resumo", headers=_auth(client))
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    corpo = r.json()
    hoje = corpo["periodos"][0]
    assert (hoje["visitas"], hoje["paginas_vistas"]) == (2, 2)
    assert corpo["periodos"][2]["visitas"] == 2
    assert len(corpo["por_dia"]) == 30
    assert corpo["por_dia"][-1]["visitas"] == 2
    assert {p["chave"] for p in corpo["paginas"]} == {"/", "/parlamentar/204554"}
    assert corpo["recursos"] == [{"chave": "cep", "total": 1}]
    assert {o["chave"] for o in corpo["origens"]} == {"whatsapp", "direto"}
    assert corpo["inicio_da_contagem"] == corpo["hoje"]


def test_resumo_limita_dias(client):
    corpo = client.get("/painel/resumo?dias=999", headers=_auth(client)).json()
    assert len(corpo["por_dia"]) == 90
    assert (
        client.get("/painel/resumo?dias=abc", headers=_auth(client)).headers["cache-control"]
        == "no-store"
    )


@pytest.mark.parametrize(
    ("usuario", "senha"), [("dono", "errada-errada"), ("outro", "senha-muito-longa"), ("", "")]
)
def test_login_errado_da_erro_generico_e_no_store(client, usuario, senha):
    r = _entrar(client, usuario, senha)
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuário ou senha incorretos."
    assert r.headers["cache-control"] == "no-store"


def test_limite_de_tentativas_por_ip(client):
    ip = {"headers": {"CF-Connecting-IP": "198.51.100.7"}}
    for _ in range(5):
        assert _entrar(client, senha="errada-errada", **ip).status_code == 401
    assert _entrar(client, **ip).status_code == 429  # nem a senha certa passa
    assert _entrar(client, headers={"CF-Connecting-IP": "198.51.100.8"}).status_code == 200


def test_resumo_exige_token(client):
    for cabecalho in ({}, {"Authorization": "Bearer lixo"}, {"Authorization": "Basic abc"}):
        r = client.get("/painel/resumo", headers=cabecalho)
        assert r.status_code == 401
        assert r.headers["cache-control"] == "no-store"


def test_token_vencido_ou_adulterado(client):
    segredo = settings.painel_segredo
    velho = painel_auth.emitir_token(segredo, agora=time.time() - 13 * 3600)
    assert not painel_auth.token_valido(velho, segredo)
    assert (
        client.get("/painel/resumo", headers={"Authorization": f"Bearer {velho}"}).status_code
        == 401
    )
    valido = painel_auth.emitir_token(segredo)
    assert painel_auth.token_valido(valido, segredo)
    assert not painel_auth.token_valido(valido, "outro-segredo")
    validade, assinatura = valido.split(".")
    esticado = f"{int(validade) + 99999}.{assinatura}"
    assert not painel_auth.token_valido(esticado, segredo)
    assert painel_auth.VALIDADE_S == int(timedelta(hours=12).total_seconds())


def test_sem_configuracao_responde_503(client, monkeypatch):
    monkeypatch.setattr(settings, "painel_segredo", "")
    for r in (_entrar(client), client.get("/painel/resumo")):
        assert r.status_code == 503
        assert r.headers["cache-control"] == "no-store"


def test_painel_nunca_tem_cors_aberto(client):
    origem = {"Origin": "http://localhost:3000"}
    respostas = [
        client.get("/painel/resumo", headers=origem),
        client.get("/painel/resumo", headers={**origem, **_auth(client)}),
        _entrar(client, headers=origem),
        client.options(
            "/painel/resumo",
            headers={
                **origem,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        ),
    ]
    for r in respostas:
        assert r.headers.get("access-control-allow-origin") != "*"
        assert r.headers["cache-control"] == "no-store"
    assert respostas[-1].headers["access-control-allow-origin"] == "http://localhost:3000"


def test_hash_da_senha():
    h = painel_auth.gerar_hash("abc")
    assert h.startswith("scrypt:") and "$" not in h
    assert painel_auth.conferir_senha("abc", h)
    assert not painel_auth.conferir_senha("abd", h)
    assert not painel_auth.conferir_senha("abc", "lixo")
    assert not painel_auth.conferir_senha("abc", "")


def test_token_com_caractere_fora_do_ascii_nao_quebra():
    assert not painel_auth.token_valido("1.é", "segredo")
