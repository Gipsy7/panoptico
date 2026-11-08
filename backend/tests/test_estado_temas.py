"""Temas de "Por dentro do estado": os serviços das cidades com o código do estado, sem a
comparação do estado com ele mesmo."""

from sqlalchemy import insert

from app.models import (
    HomicidioSim,
    IdebResultado,
    InternetFixa,
    Municipio,
    PibIbge,
    PopulacaoIbge,
    SaneamentoCenso,
)


def test_estado_desconhecido_da_404(client):
    assert client.get("/estados/XX/pib").status_code == 404


def test_pib_e_saneamento_do_estado(client, session):
    session.execute(
        insert(PibIbge),
        [{"codigo": c, "ano": 2023, "pib": v} for c, v in [("42", 500000000), ("1", 11000000000)]],
    )
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": c, "ano": 2023, "valor": v, "origem": "estimativa"}
         for c, v in [("42", 8000000), ("1", 200000000)]],
    )  # fmt: skip
    session.execute(
        insert(SaneamentoCenso),
        [{"codigo": "42", "ano": 2022, "agua_rede": 84.36, "esgoto_rede": 54.34,
          "lixo_coletado": 96.73},
         {"codigo": "1", "ano": 2022, "agua_rede": 83.88, "esgoto_rede": 64.69,
          "lixo_coletado": 91.71}],
    )  # fmt: skip
    pib = client.get("/estados/sc/pib").json()
    assert pib["serie"][0]["por_habitante"] == 500000000 * 1000 / 8000000
    assert pib["serie"][0]["uf_por_habitante"] is None
    assert pib["serie"][0]["brasil_por_habitante"] == 11000000000 * 1000 / 200000000
    san = client.get("/estados/SC/saneamento").json()
    assert san["cidade"]["esgoto_rede"] == 54.34
    assert san["estado"]["esgoto_rede"] is None
    assert san["brasil"]["esgoto_rede"] == 64.69


def test_ideb_internet_e_seguranca_do_estado(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(IdebResultado),
        [{"abrangencia": a, "codigo": c, "etapa": "iniciais", "rede": "publica", "ano": 2023,
          "valor": v} for a, c, v in [("uf", "SC", 6.4), ("brasil", "BR", 5.7)]],
    )  # fmt: skip
    session.execute(
        insert(InternetFixa),
        [{"codigo": "4202404", "ano": 2026, "mes": 9, "acessos": 100, "acessos_fibra": 50,
          "acessos_rapidos": 90}],
    )  # fmt: skip
    session.execute(
        insert(HomicidioSim),
        [{"codigo": c, "ano": 2024, "homicidios": n} for c, n in [("42", 650), ("1", 40000)]],
    )
    ideb = client.get("/estados/SC/ideb").json()
    rede = ideb["etapas"][0]["redes"][0]
    assert rede["serie"][0]["valor"] == 6.4 and rede["uf"] == []
    assert rede["brasil"][0]["valor"] == 5.7
    net = client.get("/estados/SC/internet").json()
    assert (net["acessos"], net["percentual_fibra"]) == (100, 50)
    seg = client.get("/estados/SC/seguranca").json()
    assert seg["cidade"]["serie"][0]["homicidios"] == 650
    assert seg["estado"]["serie"] == []
