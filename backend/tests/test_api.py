from decimal import Decimal

import respx
from sqlalchemy import select

from app.models import FonteIngestao, Parlamentar
from ingestion.camara import deputados
from ingestion.comum import upsert_parlamentares
from ingestion.senado import senadores
from tests.conftest import carregar_fixture


def _ingestao(session, fonte="teste"):
    ingestao = FonteIngestao(fonte=fonte, url="https://exemplo", arquivo_raw="x.json")
    session.add(ingestao)
    session.flush()
    return ingestao


def _popular(session):
    camara = deputados.normalizar(carregar_fixture("camara_deputados.json"))
    senado = senadores.normalizar(carregar_fixture("senado_senadores.json"))
    upsert_parlamentares(session, "camara", camara, _ingestao(session))
    upsert_parlamentares(session, "senado", senado, _ingestao(session))
    session.flush()
    return camara, senado


def test_saude(client):
    assert client.get("/saude").json() == {"status": "ok", "banco": "ok"}


def test_upsert_idempotente_e_marca_fora_de_exercicio(session):
    camara, _ = _popular(session)
    upsert_parlamentares(session, "camara", camara, _ingestao(session))
    total = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()
    assert len(total) == 3

    upsert_parlamentares(session, "camara", camara[:2], _ingestao(session))
    session.expire_all()
    saiu = session.scalars(
        select(Parlamentar).where(Parlamentar.id_externo == camara[2]["id_externo"])
    ).one()
    assert saiu.em_exercicio is False


def test_representantes_por_uf(client, session):
    camara, _ = _popular(session)
    uf = camara[0]["uf"]
    resposta = client.get(f"/representantes?uf={uf.lower()}")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["localizacao"]["uf"] == uf
    assert corpo["localizacao"]["municipio"] is None
    assert [d["nome_parlamentar"] for d in corpo["deputados"]] == [
        r["nome_parlamentar"] for r in camara if r["uf"] == uf
    ]
    assert corpo["atualizado_em"] is not None


@respx.mock
def test_representantes_por_cep(client, session):
    _, senado = _popular(session)
    uf = senado[0]["uf"]
    respx.get("https://viacep.com.br/ws/01001000/json/").respond(
        json={"localidade": "Cidade Teste", "uf": uf, "ibge": "1234567"}
    )
    corpo = client.get("/representantes?cep=01001-000").json()
    assert corpo["localizacao"] == {
        "cep": "01001000",
        "uf": uf,
        "estado": corpo["localizacao"]["estado"],
        "municipio": "Cidade Teste",
        "codigo_ibge": "1234567",
    }
    assert senado[0]["nome_parlamentar"] in [s["nome_parlamentar"] for s in corpo["senadores"]]


@respx.mock
def test_representantes_erros(client):
    respx.get("https://viacep.com.br/ws/99999999/json/").respond(json={"erro": "true"})
    assert client.get("/representantes").status_code == 422
    assert client.get("/representantes?cep=123").status_code == 422
    assert client.get("/representantes?uf=XX").status_code == 422
    assert client.get("/representantes?cep=99999999").status_code == 404


def test_parlamentar_detalhe(client, session):
    _popular(session)
    p = session.scalars(select(Parlamentar).where(Parlamentar.casa == "senado")).first()
    corpo = client.get(f"/parlamentares/{p.id}").json()
    assert corpo["nome_parlamentar"] == p.nome_parlamentar
    assert corpo["fonte_url"] and corpo["atualizado_em"]
    assert corpo["remuneracao"]["subsidio_mensal"] > 0
    assert client.get("/parlamentares/999999").status_code == 404


def test_remuneracao_vigente():
    from datetime import date

    from app.services import remuneracao

    assert remuneracao.vigente(date(2024, 1, 31))["subsidio_mensal"] == Decimal("41650.92")
    assert remuneracao.vigente(date(2025, 2, 1))["subsidio_mensal"] == Decimal("46366.19")
