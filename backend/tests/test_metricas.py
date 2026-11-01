# ruff: noqa: E501
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.api import metricas as rotas
from app.api import painel as rotas_painel
from app.config import settings
from app.models.camara_municipal import MandatoLocal
from app.models.candidatura import Candidatura
from app.models.metrica import MetricaDiaria
from app.models.municipio import Municipio
from app.models.parlamentar import Parlamentar
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


def _post(client, rota, corpo, headers=TEXTO):
    return client.post(f"/metricas/{rota}", content=json.dumps(corpo), headers=headers)


def _visita(client, corpo, headers=TEXTO):
    return _post(client, "visita", corpo, headers)


def _totais(session):
    """(tipo, chave) -> total, somando aparelhos e origens."""
    soma: dict = {}
    for m in session.scalars(select(MetricaDiaria)):
        soma[(m.tipo, m.chave)] = soma.get((m.tipo, m.chave), 0) + m.total
    return soma


DIMS = {"origem": "whatsapp", "aparelho": "celular"}
NOVA = {"caminho": "/parlamentar/204554", "nova": True, **DIMS}


def test_visita_nova_conta_pagina_perfil_visita_entrada(client, session):
    r = _visita(client, NOVA)
    assert r.status_code == 204
    assert r.headers["cache-control"] == "no-store"
    assert _totais(session) == {
        ("pagina", "/parlamentar/[id]"): 1,
        ("perfil", "parlamentar:204554"): 1,
        ("visita", "total"): 1,
        ("entrada", "/parlamentar/[id]"): 1,
    }
    _visita(client, {"caminho": "/parlamentar/204554", **DIMS})  # mesma visita, outra página
    totais = _totais(session)
    assert totais[("pagina", "/parlamentar/[id]")] == 2
    assert totais[("perfil", "parlamentar:204554")] == 2
    assert totais[("visita", "total")] == 1
    linha = session.scalars(select(MetricaDiaria).where(MetricaDiaria.tipo == "visita")).one()
    assert (linha.aparelho, linha.origem) == ("celular", "whatsapp")


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("/", "/"),
        ("/avisos", "/avisos"),
        ("/representantes", "/representantes"),
        ("/representantes/", "/representantes"),
        ("/representantes?cep=01310100", None),
        ("/representantes#x", None),
        ("/representantes?uf=SC", None),
        ("/cep/01310100", None),
        ("/01310100", None),
        ("/parlamentar/204554", "/parlamentar/[id]"),
        ("/parlamentar/01310100", None),
        ("/parlamentar/abc", None),
        ("/cidade/4205407", "/cidade/[ibge]"),
        ("/cidade/01310100", None),
        ("/partidos/pt", "/partidos/[sigla]"),
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


@pytest.mark.parametrize(
    ("bruto", "perfil", "partido"),
    [
        ("/parlamentar/204554", "parlamentar:204554", None),
        ("/eleito/12", "eleito:12", None),
        ("/vereador/998877", "vereador:998877", None),
        ("/deputado-estadual/5", "deputado-estadual:5", None),
        ("/projeto/camara/2345678", "projeto-camara:2345678", None),
        ("/projeto/senado/99", "projeto-senado:99", None),
        ("/projeto/local/77", "projeto-local:77", None),
        ("/partidos/pt", None, "pt"),
        ("/eleito/12345678", None, None),  # 8 dígitos: pode ser CEP, não guarda o id
        ("/projeto/camara/abc", None, None),
        ("/projeto/outra/123", None, None),
    ],
)
def test_id_de_perfil_com_formato_estrito(bruto, perfil, partido):
    c = servico.analisar_caminho(bruto)
    assert (c.perfil if c else None) == perfil
    assert (c.partido if c else None) == partido


def test_caminho_com_cep_nao_grava(client, session):
    for caminho in ("/representantes?cep=01310100", "/eleito/01310100/x", "/01310-100"):
        assert _visita(client, {**NOVA, "caminho": caminho}).status_code == 204
    assert _totais(session) == {}


def _tudo_como_texto(session) -> str:
    return " ".join(
        f"{m.tipo} {m.chave} {m.aparelho} {m.origem}"
        for m in session.scalars(select(MetricaDiaria))
    )


def test_cep_nunca_e_gravado_nem_em_beacon_malformado(client, session):
    cep = "01310100"
    malformados = [
        {**DIMS, "forma": "cep", "resultado": True, "uf": "SP", "ibge": "3550308", "cep": cep},
        {**DIMS, "forma": "cep", "resultado": True, "uf": cep},
        {**DIMS, "forma": "cep", "resultado": True, "ibge": cep},
        {**DIMS, "forma": "cep", "resultado": True, "uf": "SP", "ibge": f"{cep}9"},
        {**DIMS, "forma": cep, "resultado": True, "uf": "SP"},
        {**DIMS, "forma": "cep", "resultado": cep},
        {**DIMS, "origem": cep, "forma": "cep", "resultado": True, "uf": "SP"},
        {**DIMS, "aparelho": cep, "forma": "cep", "resultado": True, "uf": "SP"},
    ]
    for corpo in malformados:
        assert _post(client, "busca", corpo).status_code == 204
    _post(client, "recurso", {**DIMS, "recurso": cep})
    _post(client, "secao", {**DIMS, "secao": cep})
    _post(client, "saida", {**DIMS, "caminho": f"/representantes?cep={cep}"})
    _post(client, "visita", {**NOVA, "caminho": f"/representantes?cep={cep}", "cep": cep})
    assert cep not in _tudo_como_texto(session)
    assert "0131" not in _tudo_como_texto(session)
    # O primeiro corpo é aceito (só o resultado, a UF e a cidade), mas sem o CEP.
    assert _totais(session)[("uf", "SP")] == 2
    assert _totais(session)[("cidade", "3550308")] == 1


def test_busca_grava_resultado_uf_e_cidade(client, session):
    _post(
        client, "busca", {**DIMS, "forma": "cep", "resultado": True, "uf": "SC", "ibge": "4205407"}
    )
    _post(client, "busca", {**DIMS, "forma": "cep", "resultado": False})
    _post(
        client,
        "busca",
        {**DIMS, "forma": "cidade", "resultado": True, "uf": "SC", "ibge": "4205407"},
    )
    _post(client, "busca", {**DIMS, "forma": "estado", "resultado": True, "uf": "PR"})
    _post(
        client,
        "busca",
        {**DIMS, "forma": "cidade", "resultado": False, "uf": "SC", "ibge": "4205407"},
    )
    assert _totais(session) == {
        ("busca", "cep_com"): 1,
        ("busca", "cep_sem"): 1,
        ("uf", "SC"): 2,
        ("uf", "PR"): 1,
        ("cidade", "4205407"): 2,
    }


@pytest.mark.parametrize(
    "corpo",
    [
        {**DIMS, "caminho": "/", "nova": True, "origem": "texto livre"},
        {**DIMS, "caminho": "/", "nova": True, "aparelho": "tablet"},
        {"caminho": "/", "nova": True},  # sem origem e aparelho
        {**DIMS, "caminho": "/", "nova": True, "origem": None},
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
    assert _post(client, "recurso", {**DIMS, "recurso": "cep"}).status_code == 204
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


def test_recurso_secao_e_saida_so_aceitam_a_lista(client, session):
    for r in ("cep", "pix", "texto-livre", 7, None):
        _post(client, "recurso", {**DIMS, "recurso": r})
    for s in ("gastos", "votos-tema", "invento", None):
        _post(client, "secao", {**DIMS, "secao": s})
    _post(client, "saida", {**DIMS, "caminho": "/projetos"})
    _post(client, "saida", {**DIMS, "caminho": "/nao-existe"})
    assert _totais(session) == {
        ("recurso", "cep"): 1,
        ("recurso", "pix"): 1,
        ("secao", "gastos"): 1,
        ("secao", "votos-tema"): 1,
        ("ultima", "/projetos"): 1,
    }


def test_limite_por_ip_em_memoria(client, session, monkeypatch):
    monkeypatch.setattr(rotas, "LIMITE_POR_MINUTO", 3)
    for _ in range(6):
        _visita(client, {"caminho": "/", **DIMS}, {**TEXTO, "CF-Connecting-IP": "203.0.113.9"})
    assert _totais(session)[("pagina", "/")] == 3


@pytest.mark.parametrize("rota", ["visita", "recurso", "saida", "secao", "busca"])
def test_metricas_sem_cors_aberto_e_sem_cache(client, rota):
    r = _post(client, rota, NOVA, {**TEXTO, "Origin": "http://localhost:3000"})
    assert r.headers["cache-control"] == "no-store"
    assert r.headers.get("access-control-allow-origin") != "*"
    r = client.post(f"/metricas/{rota}", headers={"Content-Type": "text/plain"})  # sem user-agent
    assert r.headers["cache-control"] == "no-store"


# ---------- painel ----------


def _entrar(client, usuario="dono", senha="senha-muito-longa", **kw):
    return client.post("/painel/entrar", json={"usuario": usuario, "senha": senha}, **kw)


def _auth(client):
    token = _entrar(client).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _resumo(client, **params):
    r = client.get("/painel/resumo", params=params, headers=_auth(client))
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    return r.json()


def _linha(session, dia, tipo, chave, total, aparelho="celular", origem="whatsapp"):
    session.add(
        MetricaDiaria(
            dia=dia, tipo=tipo, chave=chave, aparelho=aparelho, origem=origem, total=total
        )
    )


def test_senha_certa_devolve_token_e_resumo(client, session):
    _visita(client, NOVA)
    _visita(client, {"caminho": "/", "nova": True, "origem": "direto", "aparelho": "computador"})
    _post(client, "recurso", {**DIMS, "recurso": "compartilhar"})
    corpo = _resumo(client)
    assert corpo["tiles"]["visitas"] == {"atual": 2, "anterior": 0}
    assert corpo["tiles"]["paginas_vistas"]["atual"] == 2
    assert corpo["tiles"]["compartilhamentos"]["atual"] == 1
    assert len(corpo["serie"]) == 7
    assert corpo["serie"][-1]["visitas"] == 2
    assert {p["chave"] for p in corpo["paginas"]} == {"/", "/parlamentar/[id]"}
    assert {o["chave"] for o in corpo["origens"]} == {"whatsapp", "direto"}
    assert corpo["inicio_da_contagem"] == corpo["hoje"]
    assert "/avisos" not in corpo["rotas_fixas"]  # página de aviso não é conteúdo


def test_resumo_limita_dias(client):
    h = _auth(client)
    assert len(client.get("/painel/resumo?dias=90", headers=h).json()["serie"]) == 90
    assert client.get("/painel/resumo?dias=999", headers=h).status_code == 422
    r = client.get("/painel/resumo?dias=abc", headers=h)
    assert r.status_code == 422
    assert r.headers["cache-control"] == "no-store"


def test_hoje_compara_com_ontem_inteiro(client, session):
    hoje = servico.hoje()
    _linha(session, hoje, "visita", "total", 10)
    _linha(session, hoje - timedelta(days=1), "visita", "total", 40)
    _linha(session, hoje - timedelta(days=2), "visita", "total", 999)  # fora das duas janelas
    session.flush()
    t = _resumo(client, dias=1)["tiles"]["visitas"]
    assert t == {"atual": 10, "anterior": 40}
    t7 = _resumo(client, dias=7)["tiles"]["visitas"]
    assert t7 == {"atual": 10 + 40 + 999, "anterior": 0}
    _linha(session, hoje - timedelta(days=8), "visita", "total", 5)
    session.flush()
    assert _resumo(client, dias=7)["tiles"]["visitas"]["anterior"] == 5


def test_filtros_cruzados_aparelho_e_origem(client, session):
    hoje = servico.hoje()
    _linha(session, hoje, "visita", "total", 10, "celular", "whatsapp")
    _linha(session, hoje, "visita", "total", 4, "computador", "google")
    _linha(session, hoje, "visita", "total", 3, "celular", "google")
    _linha(session, hoje, "pagina", "/projetos", 8, "celular", "whatsapp")
    _linha(session, hoje, "pagina", "/comparar", 5, "computador", "google")
    session.flush()
    assert _resumo(client)["tiles"]["visitas"]["atual"] == 17
    assert _resumo(client, aparelho="celular")["tiles"]["visitas"]["atual"] == 13
    assert _resumo(client, origem="google")["tiles"]["visitas"]["atual"] == 7
    r = _resumo(client, origem="google", aparelho="celular")
    assert r["tiles"]["visitas"]["atual"] == 3
    assert [p["chave"] for p in r["paginas"]] == []
    r = _resumo(client, origem="google")
    assert [p["chave"] for p in r["paginas"]] == ["/comparar"]
    # A lista de origens ignora o filtro de origem (senão só sobraria a escolhida), mas obedece ao aparelho.
    assert {o["chave"]: o["atual"] for o in r["origens"]} == {"whatsapp": 10, "google": 7}
    r = _resumo(client, origem="google", aparelho="computador")
    assert {o["chave"]: o["atual"] for o in r["origens"]} == {"google": 4}
    assert r["filtros"] == {"aparelho": "computador", "origem": "google", "uf": None}


def test_filtros_invalidos_dao_422_com_no_store(client):
    h = _auth(client)
    for q in ("aparelho=tablet", "origem=x", "uf=XX", "uf=sc"):
        r = client.get(f"/painel/resumo?{q}", headers=h)
        assert r.status_code == 422, q
        assert r.headers["cache-control"] == "no-store"


def test_item_mostra_a_serie_da_pagina_sem_filtrar_o_resto(client, session):
    hoje = servico.hoje()
    _linha(session, hoje, "pagina", "/projetos", 8)
    _linha(session, hoje - timedelta(days=1), "pagina", "/projetos", 2)
    _linha(session, hoje, "pagina", "/comparar", 5)
    _linha(session, hoje, "visita", "total", 6)
    session.flush()
    r = _resumo(client, item="pagina:/projetos")
    assert r["item"]["atual"] == 10
    assert r["item"]["serie"][-1] == {"dia": hoje.isoformat(), "total": 8}
    assert r["tiles"]["visitas"]["atual"] == 6  # o resto não foi filtrado
    assert {p["chave"] for p in r["paginas"]} == {"/projetos", "/comparar"}
    assert _resumo(client, item="invento:x")["item"] is None
    assert _resumo(client, item="perfil:eleito:abc")["item"] is None


def test_cidade_abaixo_de_cinco_buscas_nao_sai(client, session):
    hoje = servico.hoje()
    session.add_all(
        [
            Municipio(ibge="4205407", nome="Florianópolis", uf="SC", nome_chave="FLORIANOPOLIS"),
            Municipio(ibge="4202008", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"),
            Municipio(ibge="4106902", nome="Curitiba", uf="PR", nome_chave="CURITIBA"),
        ]
    )
    _linha(session, hoje, "cidade", "4205407", 3)
    _linha(session, hoje, "cidade", "4205407", 2, "computador", "google")  # 5 no total
    _linha(session, hoje, "cidade", "4202008", 4)
    _linha(session, hoje, "cidade", "4106902", 9)
    _linha(session, hoje, "cidade", "9999999", 50)  # não existe no IBGE: nunca aparece
    session.flush()
    c = _resumo(client)["cidades"]
    assert [(x["nome"], x["total"]) for x in c["itens"]] == [("Curitiba", 9), ("Florianópolis", 5)]
    assert c["fora"] == 1 and c["minimo"] == 5
    assert "Blumenau" not in json.dumps(c)
    # O filtro de estado vale para a lista de cidades.
    c = _resumo(client, uf="SC")["cidades"]
    assert [x["nome"] for x in c["itens"]] == ["Florianópolis"]
    # Com o filtro de aparelho, Florianópolis cai para 3 e some.
    assert [x["nome"] for x in _resumo(client, aparelho="celular")["cidades"]["itens"]] == [
        "Curitiba"
    ]


def test_uf_e_regiao_vem_do_servidor(client, session):
    hoje = servico.hoje()
    _linha(session, hoje, "uf", "SC", 6)
    _linha(session, hoje, "uf", "PR", 4)
    _linha(session, hoje, "uf", "BA", 3)
    session.flush()
    r = _resumo(client)
    assert {u["uf"]: u["total"] for u in r["ufs"]} == {"SC": 6, "PR": 4, "BA": 3}
    assert {x["chave"]: x["total"] for x in r["regioes"]} == {"Sul": 10, "Nordeste": 3}


def test_representantes_so_com_id_existente_e_com_nome_do_banco(client, session):
    hoje = servico.hoje()
    p = Parlamentar(
        casa="camara",
        id_externo="1",
        nome_parlamentar="Fulana Teste",
        uf="SC",
        partido="XYZ",
        fonte_url="x",
        atualizado_em=datetime.now(UTC),
    )
    c = Candidatura(
        ano_eleicao=2024,
        sq_candidato="1",
        cargo="VEREADOR",
        uf="PR",
        unidade="Curitiba",
        nome="Beltrano Souza",
        nome_urna="Beltrano",
        partido="ABC",
    )
    session.add_all([p, c])
    session.flush()
    _linha(session, hoje, "perfil", f"parlamentar:{p.id}", 7)
    _linha(session, hoje, "perfil", f"eleito:{c.id}", 3)
    _linha(session, hoje, "perfil", "parlamentar:9999999", 100)  # não existe
    _linha(session, hoje, "perfil", "vereador:9999998", 100)  # não existe
    _linha(session, hoje - timedelta(days=8), "perfil", f"parlamentar:{p.id}", 2)
    _linha(session, hoje, "partido", "xyz", 5)
    _linha(session, hoje, "partido", "inexistente", 50)
    session.flush()
    r = _resumo(client)
    reps = {x["nome"]: x for x in r["representantes"]}
    assert set(reps) == {"Fulana Teste", "Beltrano"}
    assert reps["Fulana Teste"]["cargo"] == "Deputado federal"
    f = reps["Fulana Teste"]
    assert (f["uf"], f["atual"], f["anterior"]) == ("SC", 7, 2)
    assert reps["Beltrano"]["cargo"] == "Vereador" and reps["Beltrano"]["partido"] == "ABC"
    assert [x["chave"] for x in r["partidos"]] == ["XYZ"]
    d = _resumo(client, item=f"perfil:parlamentar:{p.id}")["item"]
    assert d["rotulo"] == "Fulana Teste" and d["atual"] == 7
    assert _resumo(client, item="perfil:parlamentar:9999999")["item"] is None


def test_mandato_local_define_vereador_ou_deputado_estadual(client, session):
    hoje = servico.hoje()
    a = MandatoLocal(casa="camara", uf="SC", id_externo="1", nome="Vera", sapl_url="x")
    b = MandatoLocal(casa="assembleia", uf="SC", id_externo="2", nome="Dani", sapl_url="x")
    session.add_all([a, b])
    session.flush()
    _linha(session, hoje, "perfil", f"vereador:{a.id}", 2)
    _linha(session, hoje, "perfil", f"deputado-estadual:{b.id}", 1)
    session.flush()
    cargos = {x["nome"]: x["cargo"] for x in _resumo(client)["representantes"]}
    assert cargos == {"Vera": "Vereador", "Dani": "Deputado estadual"}


def test_sem_visita_menos_vistas_e_dia_da_semana(client, session):
    hoje = servico.hoje()
    _linha(session, hoje, "pagina", "/projetos", 9)
    _linha(session, hoje, "pagina", "/privacidade", 1)
    _linha(session, hoje - timedelta(days=9), "pagina", "/comparar", 4)
    session.flush()
    r = _resumo(client)
    por = {p["chave"]: p for p in r["paginas"]}
    assert por["/privacidade"]["conteudo"] is False
    assert por["/comparar"]["atual"] == 0 and por["/comparar"]["anterior"] == 4
    assert "/projetos" in r["rotas_fixas"] and "/avisos" not in r["rotas_fixas"]
    semana = {d["dia"]: d for d in r["uso"]["dia_da_semana"]}
    assert sum(d["dias"] for d in semana.values()) == 7
    assert len(r["uso"]["dia_da_semana"]) == 7


def test_uso_entrada_ultima_secao_e_cep(client, session):
    _visita(client, {"caminho": "/projetos", "nova": True, **DIMS})
    _visita(client, {"caminho": "/comparar", **DIMS})
    _post(client, "saida", {**DIMS, "caminho": "/comparar"})
    _post(client, "secao", {**DIMS, "secao": "gastos"})
    _post(client, "busca", {**DIMS, "forma": "cep", "resultado": True, "uf": "SC"})
    _post(client, "busca", {**DIMS, "forma": "cep", "resultado": False})
    uso = _resumo(client)["uso"]
    assert [x["chave"] for x in uso["entradas"]] == ["/projetos"]
    assert [x["chave"] for x in uso["ultimas"]] == ["/comparar"]
    assert [x["chave"] for x in uso["secoes"]] == ["gastos"]
    assert (uso["cep"]["com"], uso["cep"]["sem"]) == (1, 1)


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
