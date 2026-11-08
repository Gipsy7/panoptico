"""Saúde no CNES (DATASUS): contagem por tipo, campos guardados, normalização e rotas."""

import pytest
from sqlalchemy import insert

from app.models import Municipio, PopulacaoIbge, SaudeCnes
from ingestion.datasus import cnes


def test_contagens_por_tipo_e_campos():
    mun: dict = {}
    cnes.contar_leitos(
        [{"CODUFMUN": "420240", "TP_LEITO": "1", "QT_EXIST": "10", "QT_SUS": "6"},
         {"CODUFMUN": "420240", "TP_LEITO": "3", "QT_EXIST": "4", "QT_SUS": "2"},
         {"CODUFMUN": "420240", "TP_LEITO": "2", "QT_EXIST": "", "QT_SUS": ""}],
        mun,
    )  # fmt: skip
    cnes.contar_unidades(
        [{"CODUFMUN": "420240", "TP_UNID": t} for t in ("02", "01", "05", "22", "15")], mun
    )
    v = cnes.campos_de(mun["420240"])
    assert (v["leitos"], v["leitos_sus"]) == (10, 6)  # complementar fica à parte
    assert (v["leitos_complementares"], v["leitos_complementares_sus"]) == (4, 2)
    assert (v["ubs"], v["hospitais"]) == (2, 2)  # consultório (22) não conta


def test_normalizar_soma_estado_e_brasil_e_zera_cidade_sem_dado():
    bruto = {"leitos": {"1": [10, 5]}, "unidades": {"02": 3}}
    recorte = {
        "competencia": "202609",
        "ufs": {"SC": {"420240": bruto, "420000": bruto}, "RR": {"140010": bruto}},
    }
    mapa6 = {"420240": "4202404", "420910": "4209102", "140010": "1400100"}
    linhas = {r["codigo"]: r for r in cnes.normalizar(recorte, mapa6)}
    assert linhas["4202404"]["leitos"] == 10
    assert linhas["4209102"]["leitos"] == 0
    assert linhas["42"]["leitos"] == 20  # o código ignorado conta no estado
    assert linhas["1"]["ubs"] == 9
    assert (linhas["1"]["ano"], linhas["1"]["mes"]) == (2026, 9)


def test_carregar_aborta_sem_as_27_ufs(session):
    with pytest.raises(ValueError):
        cnes.carregar(session, {"competencia": "202609", "ufs": {"SC": {}}}, None)


def _popular(session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(SaudeCnes),
        [{"codigo": c, "ano": 2026, "mes": 9, "leitos": lt, "leitos_sus": lt // 2,
          "leitos_complementares": 10, "leitos_complementares_sus": 5, "ubs": u, "hospitais": 1}
         for c, lt, u in [("4202404", 800, 60), ("42", 16000, 2000), ("1", 460000, 50000)]],
    )  # fmt: skip
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": c, "ano": 2025, "valor": v, "origem": "estimativa"}
         for c, v in [("4202404", 400000), ("42", 8000000), ("1", 200000000)]],
    )  # fmt: skip


def test_rota_da_saude(client, session):
    _popular(session)
    corpo = client.get("/municipios/4202404/saude").json()
    assert (corpo["ano"], corpo["mes"]) == (2026, 9)
    assert corpo["cidade"]["leitos_por_mil"] == pytest.approx(2.0)
    assert corpo["cidade"]["ubs_por_10_mil"] == pytest.approx(1.5)
    assert corpo["estado"]["leitos_por_mil"] == pytest.approx(2.0)
    assert corpo["brasil"]["leitos_por_mil"] == pytest.approx(2.3)
    assert client.get("/municipios/9999999/saude").status_code == 404
    uf = client.get("/estados/SC/saude").json()
    assert uf["cidade"]["leitos"] == 16000 and uf["estado"] is None
