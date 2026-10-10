from datetime import date

from sqlalchemy import select

from app.models import Candidatura, Parlamentar
from tests.test_api import _ingestao, _popular

ANO = date.today().year  # eleição sem posse (o ano da eleição); ANO - 4 é o mandato de hoje


def _cand(session, ingestao, nome, cargo, situacao, ano=ANO, uf="SC", **campos):
    c = Candidatura(
        ano_eleicao=ano,
        sq_candidato=f"{abs(hash((nome, ano, cargo))) % 10**15}",
        cargo=cargo,
        uf=uf,
        unidade="Santa Catarina" if uf == "SC" else "Brasil",
        nome=nome,
        nome_urna=nome,
        partido="PP",
        situacao_turno=situacao,
        ingestao_id=ingestao,
        **campos,
    )
    session.add(c)
    session.flush()
    return c


def test_eleitos_do_estado_separados_do_cargo_de_hoje(client, session):
    ingestao = _ingestao(session).id
    _cand(session, ingestao, "Nova Federal", "DEPUTADO FEDERAL", "ELEITO POR QP")
    _cand(session, ingestao, "Nao Eleita", "DEPUTADO FEDERAL", "NÃO ELEITO")
    _cand(session, ingestao, "Suplente", "DEPUTADO FEDERAL", "SUPLENTE")
    _cand(session, ingestao, "Nova Estadual", "DEPUTADO ESTADUAL", "ELEITO POR MÉDIA")
    _cand(session, ingestao, "Senador Novo", "SENADOR", "ELEITO")
    gov = _cand(session, ingestao, "Governo Dois", "GOVERNADOR", "2º TURNO")
    _cand(session, ingestao, "Vice Dois", "VICE-GOVERNADOR", "2º TURNO", chapa_titular_id=gov.id)
    _cand(session, ingestao, "Outro Estado", "DEPUTADO FEDERAL", "ELEITO POR QP", uf="RS")
    _cand(session, ingestao, "Pres Dois", "PRESIDENTE", "2º TURNO", uf="BR")
    _cand(session, ingestao, "Velho Mandato", "DEPUTADO FEDERAL", "ELEITO POR QP", ano=ANO - 4)

    corpo = client.get("/estados/sc/eleitos-2026").json()
    assert corpo["ano_eleicao"] == ANO
    assert [i["nome_urna"] for i in corpo["deputados_federais"]] == ["Nova Federal"]
    federal = corpo["deputados_federais"][0]
    assert federal["situacao"] == "Eleito pelo quociente partidário"
    assert federal["posse"] == f"{ANO + 1}-02-01"
    assert federal["segundo_turno"] is False
    assert corpo["deputados_estaduais"][0]["situacao_tse"] == "ELEITO POR MÉDIA"
    assert corpo["senadores"][0]["posse"] == f"{ANO + 1}-02-01"
    governador = corpo["governador"][0]
    assert (governador["segundo_turno"], governador["vice"]) == (True, "Vice Dois")
    assert governador["posse"] == f"{ANO + 1}-01-01"
    assert governador["situacao"] == "Disputa o 2º turno"
    assert [i["nome_urna"] for i in corpo["presidente"]] == ["Pres Dois"]
    assert client.get("/estados/xx/eleitos-2026").status_code == 404


def test_no_cargo_hoje_nao_muda_com_eleitos_de_2026(client, session):
    camara, _ = _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    _cand(
        session,
        _ingestao(session).id,
        "Reeleito",
        "DEPUTADO FEDERAL",
        "ELEITO POR QP",
        uf=p.uf,
        parlamentar_id=p.id,
    )
    corpo = client.get(f"/representantes?uf={p.uf}").json()
    assert len(corpo["deputados"]) == len([c for c in camara if c["uf"] == p.uf])
    assert "Reeleito" not in str(corpo)
    futuros = client.get(f"/estados/{p.uf}/eleitos-2026").json()["deputados_federais"]
    assert futuros[0]["ja_no_cargo"] is True and futuros[0]["parlamentar_id"] == p.id


def test_perfil_do_reeleito_mostra_as_duas_coisas(client, session):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    ingestao = _ingestao(session).id
    _cand(session, ingestao, "Reeleito", "DEPUTADO FEDERAL", "ELEITO POR QP", ano=ANO - 4,
          uf=p.uf, parlamentar_id=p.id)  # fmt: skip
    _cand(session, ingestao, "Reeleito", "DEPUTADO FEDERAL", "ELEITO POR QP", uf=p.uf,
          parlamentar_id=p.id)  # fmt: skip
    corpo = client.get(f"/parlamentares/{p.id}/candidatura").json()
    assert len(corpo["candidaturas"]) == 2
    assert corpo["eleito_2026"]["posse"] == f"{ANO + 1}-02-01"
    assert corpo["eleito_2026"]["ja_no_cargo"] is True
    assert corpo["votos"] is None or corpo["votos"]["ano"] == ANO - 4


def test_perfil_do_eleito_novo_e_ligacao_por_titulo(client, session):
    ingestao = _ingestao(session).id
    nova = _cand(session, ingestao, "Nova Senadora", "SENADOR", "ELEITO", titulo="123")
    antiga = _cand(session, ingestao, "Nova Senadora", "VEREADOR", "ELEITO", ano=ANO - 2,
                   titulo="123")  # fmt: skip
    derrotado = _cand(session, ingestao, "Derrotado", "SENADOR", "NÃO ELEITO")
    novo = client.get(f"/eleitos/{nova.id}").json()
    assert novo["eleito_2026"]["cargo"] == "Senador"
    assert client.get(f"/eleitos/{antiga.id}").json()["eleito_2026"]["id"] == nova.id
    assert client.get(f"/eleitos/{derrotado.id}").status_code == 200
    assert client.get(f"/eleitos/{derrotado.id}").json()["eleito_2026"] is None
    federal_velha = _cand(session, ingestao, "Antigo", "SENADOR", "ELEITO", ano=ANO - 4)
    assert client.get(f"/eleitos/{federal_velha.id}").status_code == 404


def test_busca_acha_quem_so_tem_a_candidatura_eleita_de_2026(client, session):
    ingestao = _ingestao(session).id
    _cand(session, ingestao, "Zuleica Futura", "DEPUTADO FEDERAL", "ELEITO POR QP")
    _cand(session, ingestao, "Zuleica Segundo", "GOVERNADOR", "2º TURNO")
    _cand(session, ingestao, "Zuleica Perdeu", "DEPUTADO FEDERAL", "NÃO ELEITO")
    corpo = client.get("/busca?q=zuleica").json()
    assert corpo["itens"] == []
    rotulos = {i["nome"]: i["cargo"] for i in corpo["eleitos_2026"]}
    assert rotulos == {
        "Zuleica Futura": f"Deputado federal, eleito em {ANO}",
        "Zuleica Segundo": f"Governador, disputa o 2º turno de {ANO}",
    }
