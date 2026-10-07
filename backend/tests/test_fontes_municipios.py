from datetime import UTC, datetime

from sqlalchemy import insert

from app.models import FonteIngestao, Municipio
from tests.test_api import _popular

MUNICIPIOS = [
    {"ibge": "1721000", "nome": "Palmas", "uf": "TO", "nome_chave": "PALMAS"},
    {"ibge": "1700251", "nome": "Abreulândia", "uf": "TO", "nome_chave": "ABREULANDIA"},
    {"ibge": "1600303", "nome": "Macapá", "uf": "AP", "nome_chave": "MACAPA"},
]


def test_municipios_da_uf_em_ordem(client, session):
    session.execute(insert(Municipio), MUNICIPIOS)
    corpo = client.get("/municipios?uf=to").json()
    assert [m["nome"] for m in corpo] == ["Abreulândia", "Palmas"]
    assert client.get("/municipios?uf=t").status_code == 422


def test_representantes_por_municipio(client, session):
    _popular(session)
    session.execute(insert(Municipio), MUNICIPIOS)
    corpo = client.get("/representantes?municipio=1600303").json()
    assert corpo["localizacao"] == {
        "cep": None,
        "uf": "AP",
        "estado": "Amapá",
        "municipio": "Macapá",
        "codigo_ibge": "1600303",
    }
    assert client.get("/representantes?municipio=0000000").status_code == 404


def test_fontes_usa_a_carga_mais_antiga_do_item(client, session):
    def carga(fonte, dia, status="ok"):
        return {
            "fonte": fonte, "url": "u", "arquivo_raw": "a", "status": status,
            "concluido_em": datetime(2026, 10, dia, 12, tzinfo=UTC),
        }  # fmt: skip

    session.execute(
        insert(FonteIngestao),
        [
            carga("camara_despesas", 5),
            carga("senado_despesas", 3),
            carga("senado_despesas", 6, status="erro"),
        ],
    )
    fontes = {f["dado"]: f for f in client.get("/fontes").json()}
    assert fontes["Gastos do gabinete (cota parlamentar)"]["atualizado_em"].startswith("2026-10-03")
    assert fontes["Lista de municípios"]["atualizado_em"] is None
