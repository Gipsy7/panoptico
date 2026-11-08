"""Banda larga fixa (Anatel): soma do último mês por município e conta por 100 moradores."""

from sqlalchemy import insert

from app.models import InternetFixa, Municipio, PopulacaoIbge
from ingestion.anatel import banda_larga


def _linha(ano, mes, ibge, acessos, tecnologia="FTTH", faixa="> 34Mbps"):
    return {
        "Ano": str(ano),
        "Mês": str(mes),
        "Código IBGE Município": ibge,
        "Acessos": str(acessos),
        "Tecnologia": tecnologia,
        "Faixa de Velocidade": faixa,
    }


def test_somar_fica_com_o_ultimo_mes_e_separa_fibra_e_velocidade():
    linhas = [
        _linha(2026, 8, "4202404", 999),
        _linha(2026, 9, "4202404", 100),
        _linha(2026, 9, "4202404", 20, tecnologia="ADSL1", faixa="0Kbps a 512Kbps"),
        _linha(2026, 9, "", 5),  # sem código: fora
        _linha(2026, 9, "4202404", "x"),  # número inválido: fora
    ]
    r = banda_larga.somar(linhas)
    assert (r["ano"], r["mes"]) == (2026, 9)
    assert r["municipios"]["4202404"] == [120, 100, 100]


def test_rota_da_internet_por_100_moradores(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.add(
        Municipio(ibge="4205407", nome="Florianópolis", uf="SC", nome_chave="FLORIANOPOLIS")
    )
    session.flush()
    session.execute(
        insert(InternetFixa),
        [{"codigo": "4202404", "ano": 2026, "mes": 9, "acessos": 150000, "acessos_fibra": 120000,
          "acessos_rapidos": 135000},
         {"codigo": "4205407", "ano": 2026, "mes": 9, "acessos": 250000, "acessos_fibra": 1,
          "acessos_rapidos": 1}],
    )  # fmt: skip
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": c, "ano": 2025, "valor": v, "origem": "estimativa"}
         for c, v in [("4202404", 390000), ("42", 8000000), ("1", 213000000)]],
    )  # fmt: skip
    corpo = client.get("/municipios/4202404/internet").json()
    assert (corpo["ano"], corpo["mes"]) == (2026, 9)
    assert round(corpo["por_100_moradores"], 1) == round(100 * 150000 / 390000, 1)
    assert round(corpo["uf_por_100_moradores"], 2) == round(100 * 400000 / 8000000, 2)
    assert corpo["percentual_fibra"] == 80
    assert client.get("/municipios/9999999/internet").status_code == 404
