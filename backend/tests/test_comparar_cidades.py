"""Cidades parecidas e vocações: só dados já carregados (população, PIB, IDEB, CEMPRE)."""

from sqlalchemy import insert

from app.models import (
    EmpregoIbge,
    EmpregoSetor,
    IdebResultado,
    Municipio,
    PibIbge,
    PopulacaoIbge,
)

CIDADES = [("4202404", "Blumenau", 390371), ("3506003", "Bauru", 394028),
           ("3510609", "Carapicuíba", 398772), ("4205407", "Florianópolis", 576361),
           ("4204202", "Chapecó", 274000)]  # fmt: skip


def _popular(session):
    for ibge, nome, _ in CIDADES:
        session.add(Municipio(ibge=ibge, nome=nome, uf="SC", nome_chave=nome.upper()))
    session.flush()
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": c, "ano": 2025, "valor": p, "origem": "estimativa"} for c, _, p in CIDADES]
        + [{"codigo": "4202404", "ano": 2022, "valor": 361261, "origem": "censo"}],
    )
    session.execute(
        insert(PibIbge),
        [
            {"codigo": "4202404", "ano": 2022, "pib": 22791289},
            {"codigo": "4202404", "ano": 2021, "pib": 20579490, "vab_total": 1000,
             "vab_agropecuaria": 7, "vab_industria": 272, "vab_servicos": 605,
             "vab_administracao": 116},
            {"codigo": "1", "ano": 2021, "pib": 9000000000, "vab_total": 1000,
             "vab_agropecuaria": 77, "vab_industria": 258, "vab_servicos": 507,
             "vab_administracao": 158},
        ],
    )  # fmt: skip
    session.execute(
        insert(IdebResultado),
        [{"abrangencia": "municipio", "codigo": "4202404", "etapa": "iniciais", "rede": "publica",
          "ano": 2025, "valor": 6.6}],
    )  # fmt: skip
    session.execute(
        insert(EmpregoIbge),
        [{"codigo": "4202404", "ano": 2024, "pessoal_ocupado": 198372, "salario_medio": 4069.1}],
    )
    session.execute(
        insert(EmpregoSetor),
        [{"codigo": c, "ano": 2024, "secao": s, "nome": n, "pessoal_ocupado": v}
         for c, s, n, v in [("4202404", "C", "Indústria", 239), ("4202404", "G", "Comércio", 761),
                            ("1", "C", "Indústria", 128), ("1", "G", "Comércio", 872)]],
    )  # fmt: skip


def test_parecidas_pela_populacao_em_ordem_de_tamanho(client, session):
    _popular(session)
    corpo = client.get("/municipios/4202404/parecidas").json()
    assert corpo["ano_populacao"] == 2025
    nomes = [c["nome"] for c in corpo["cidades"]]
    assert nomes == ["Florianópolis", "Carapicuíba", "Bauru", "Blumenau", "Chapecó"]
    b = next(c for c in corpo["cidades"] if c["esta"])
    # PIB por morador só com população do mesmo ano (2022), não com a de 2025.
    assert round(b["pib_por_morador"]) == round(22791289 * 1000 / 361261)
    assert b["pib_ano"] == 2022 and b["ideb"] == 6.6 and b["salario_medio"] == 4069.1
    bauru = next(c for c in corpo["cidades"] if c["nome"] == "Bauru")
    assert bauru["pib_por_morador"] is None and bauru["ideb"] is None


def test_vocacoes_comparam_com_o_brasil(client, session):
    _popular(session)
    v = client.get("/municipios/4202404/vocacoes").json()
    assert v["pib_ano"] == 2021
    industria = next(x for x in v["pib"] if x["atividade"] == "Indústria")
    assert (
        round(industria["percentual"], 1) == 27.2
        and round(industria["percentual_brasil"], 1) == 25.8
    )
    assert v["emprego_ano"] == 2024
    assert v["emprego"][0]["atividade"] == "Indústria"  # maior razão primeiro
    assert round(v["emprego"][0]["razao"], 2) == round(23.9 / 12.8, 2)
    assert client.get("/municipios/9999999/vocacoes").status_code == 404
