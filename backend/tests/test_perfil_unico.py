from datetime import date

from sqlalchemy import select

from app.models import BemDeclarado, Candidatura, Foto, Parlamentar
from app.services import perfil_unico
from tests.test_api import _ingestao, _popular
from tests.test_eleitos_futuros import ANO, _cand


def _foto(session, c):
    session.add(Foto(candidatura_id=c.id, webp=b"RIFF"))
    session.flush()


def test_candidatura_nova_de_quem_ja_governa_aponta_para_o_perfil_atual(client, session):
    ingestao = _ingestao(session).id
    atual = _cand(session, ingestao, "Governador Reeleito", "GOVERNADOR", "ELEITO", ano=ANO - 4,
                  titulo="777")  # fmt: skip
    nova = _cand(session, ingestao, "Governador Reeleito", "GOVERNADOR", "ELEITO", titulo="777")
    _foto(session, atual)
    corpo = client.get(f"/eleitos/{nova.id}").json()
    assert corpo["perfil_principal"] == f"/eleito/{atual.id}"
    # O perfil atual não aponta para si nem para a candidatura nova.
    principal = client.get(f"/eleitos/{atual.id}").json()
    assert principal["perfil_principal"] is None
    assert principal["eleito_2026"]["id"] == nova.id
    assert principal["eleito_2026"]["perfil"] == f"/eleito/{atual.id}"


def test_primeira_eleicao_continua_com_a_propria_pagina(client, session):
    ingestao = _ingestao(session).id
    nova = _cand(session, ingestao, "Estreante", "GOVERNADOR", "ELEITO", titulo="888")
    corpo = client.get(f"/eleitos/{nova.id}").json()
    assert corpo["perfil_principal"] is None
    lista = client.get("/estados/sc/eleitos-2026").json()["governador"]
    assert lista[0]["perfil"] == f"/eleito/{nova.id}"


def test_nao_eleito_em_2026_nao_e_redirecionado(client, session):
    ingestao = _ingestao(session).id
    _cand(session, ingestao, "Derrotado", "GOVERNADOR", "ELEITO", ano=ANO - 4, titulo="999")
    perdeu = _cand(session, ingestao, "Derrotado", "GOVERNADOR", "NÃO ELEITO", titulo="999")
    assert client.get(f"/eleitos/{perdeu.id}").json()["perfil_principal"] is None


def test_parlamentar_reeleito_aponta_para_o_parlamentar(client, session):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    ingestao = _ingestao(session).id
    nova = _cand(session, ingestao, "Reeleito", "DEPUTADO FEDERAL", "ELEITO POR QP", uf=p.uf,
                 parlamentar_id=p.id)  # fmt: skip
    assert client.get(f"/eleitos/{nova.id}").json()["perfil_principal"] == f"/parlamentar/{p.id}"
    item = client.get(f"/estados/{p.uf}/eleitos-2026").json()["deputados_federais"][0]
    assert item["perfil"] == f"/parlamentar/{p.id}"


def test_perfil_principal_traz_bens_e_votos_de_2026(client, session):
    ingestao = _ingestao(session).id
    atual = _cand(session, ingestao, "Reeleito", "GOVERNADOR", "ELEITO", ano=ANO - 4, titulo="555")
    nova = _cand(session, ingestao, "Reeleito", "GOVERNADOR", "ELEITO", titulo="555", votos=1234)
    session.add(
        BemDeclarado(candidatura_id=atual.id, ordem=1, tipo="Casa", descricao="", valor=100)
    )
    session.add(BemDeclarado(candidatura_id=nova.id, ordem=1, tipo="Casa", descricao="", valor=250))
    session.flush()
    corpo = client.get(f"/eleitos/{atual.id}").json()
    recente = corpo["eleicao_recente"]
    assert recente["id"] == nova.id and recente["ano_eleicao"] == ANO
    assert float(recente["bens"]["total"]) == 250
    assert float(recente["bens"]["anterior"]["total"]) == 100
    assert corpo["eleito_2026"]["votos"] == 1234
    # A página da candidatura nova não repete o bloco.
    assert client.get(f"/eleitos/{nova.id}").json()["eleicao_recente"] is None


def test_foto_emprestada_da_candidatura_mais_recente_com_foto(client, session):
    ingestao = _ingestao(session).id
    velha = _cand(session, ingestao, "Sem Foto", "VEREADOR", "ELEITO", ano=ANO - 6, titulo="321")
    media = _cand(session, ingestao, "Sem Foto", "VEREADOR", "ELEITO", ano=ANO - 2, titulo="321")
    nova = _cand(session, ingestao, "Sem Foto", "DEPUTADO ESTADUAL", "ELEITO", titulo="321")
    _foto(session, velha)
    _foto(session, media)
    corpo = client.get(f"/eleitos/{nova.id}").json()
    assert (corpo["foto"], corpo["foto_de"], corpo["foto_ano"]) == (True, media.id, ANO - 2)
    propria = client.get(f"/eleitos/{media.id}").json()
    assert (propria["foto"], propria["foto_de"], propria["foto_ano"]) == (True, None, None)
    item = client.get("/estados/sc/eleitos-2026").json()["deputados_estaduais"][0]
    assert (item["foto"], item["foto_de"], item["foto_ano"]) == (True, media.id, ANO - 2)
    sem = _cand(session, ingestao, "Ninguem", "DEPUTADO ESTADUAL", "ELEITO", titulo="000")
    assert client.get(f"/eleitos/{sem.id}").json()["foto"] is False


def test_busca_leva_ao_perfil_principal_sem_repetir(client, session):
    ingestao = _ingestao(session).id
    atual = _cand(session, ingestao, "Marlene Dupla", "GOVERNADOR", "ELEITO", ano=ANO - 4,
                  titulo="444")  # fmt: skip
    _cand(session, ingestao, "Marlene Dupla", "GOVERNADOR", "ELEITO", titulo="444")
    corpo = client.get("/busca?q=marlene").json()
    caminhos = [i["caminho"] for i in corpo["itens"]] + [
        i["caminho"] for i in corpo["eleitos_2026"]
    ]
    assert caminhos == [f"/eleito/{atual.id}"]
    assert date.today().year == ANO and Candidatura  # só para deixar claro de que ano se fala


def _depois_da_posse(monkeypatch):
    monkeypatch.setattr(perfil_unico, "hoje", lambda: date(ANO + 1, 3, 1))


def test_posse_governador_e_em_1_de_janeiro_e_do_congresso_em_1_de_fevereiro():
    assert perfil_unico.data_posse("GOVERNADOR", 2026) == date(2027, 1, 1)
    assert perfil_unico.data_posse("SENADOR", 2026) == date(2027, 2, 1)


def test_antes_da_posse_a_nova_aponta_para_a_antiga(client, session, monkeypatch):
    monkeypatch.setattr(perfil_unico, "hoje", lambda: date(ANO, 12, 31))
    ingestao = _ingestao(session).id
    antiga = _cand(session, ingestao, "Gov Simetrico", "GOVERNADOR", "ELEITO", ano=ANO - 4,
                   titulo="111")  # fmt: skip
    nova = _cand(session, ingestao, "Gov Simetrico", "GOVERNADOR", "ELEITO", titulo="111")
    assert client.get(f"/eleitos/{nova.id}").json()["perfil_principal"] == f"/eleito/{antiga.id}"
    assert client.get(f"/eleitos/{antiga.id}").json()["perfil_principal"] is None


def test_depois_da_posse_a_antiga_aponta_para_a_nova(client, session, monkeypatch):
    ingestao = _ingestao(session).id
    antiga = _cand(session, ingestao, "Gov Simetrico", "GOVERNADOR", "ELEITO", ano=ANO - 4,
                   titulo="111")  # fmt: skip
    nova = _cand(session, ingestao, "Gov Simetrico", "GOVERNADOR", "ELEITO", titulo="111")
    _depois_da_posse(monkeypatch)
    assert client.get(f"/eleitos/{antiga.id}").json()["perfil_principal"] == f"/eleito/{nova.id}"
    assert client.get(f"/eleitos/{nova.id}").json()["perfil_principal"] is None


def test_depois_da_posse_parlamentar_nao_e_redirecionado(session, monkeypatch):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    ingestao = _ingestao(session).id
    antiga = _cand(session, ingestao, "Fed", "DEPUTADO FEDERAL", "ELEITO", ano=ANO - 4,
                   parlamentar_id=p.id, titulo="222")  # fmt: skip
    _cand(session, ingestao, "Fed", "DEPUTADO FEDERAL", "ELEITO", parlamentar_id=p.id,
          titulo="222")  # fmt: skip
    _depois_da_posse(monkeypatch)
    assert perfil_unico.principais(session, [antiga]) == {}
