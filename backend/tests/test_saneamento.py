"""Saneamento no Censo 2022 (IBGE): normalização das três tabelas e rota com estado e Brasil."""

from decimal import Decimal

import pytest
from sqlalchemy import insert

from app.models import Municipio, SaneamentoCenso
from ingestion.ibge import saneamento


def _recorte():
    return {
        "ano": 2022,
        "valores": {
            "agua_rede": {"4202404": "93.97", "42": "84.36", "1": "83.88"},
            "esgoto_rede": {"4202404": "67.62", "42": "54.34", "1": "64.69"},
            "lixo_coletado": {"4202404": "-", "42": "96.73", "1": "91.71", "9999999": "..."},
        },
    }


def test_normalizar_junta_as_tabelas_e_trata_ausentes():
    linhas = {r["codigo"]: r for r in saneamento.normalizar(_recorte())}
    assert linhas["4202404"]["agua_rede"] == Decimal("93.97")
    assert linhas["4202404"]["esgoto_rede"] == Decimal("67.62")
    assert linhas["4202404"]["lixo_coletado"] is None
    assert "9999999" not in linhas  # só ausentes: fora


def test_carregar_aborta_com_poucos_municipios(session):
    with pytest.raises(ValueError):
        saneamento.carregar(session, _recorte(), type("I", (), {"id": None})())


def test_rota_do_saneamento(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(SaneamentoCenso),
        [{"codigo": c, "ano": 2022, "agua_rede": a, "esgoto_rede": e, "lixo_coletado": li}
         for c, a, e, li in [("4202404", 93.97, 67.62, 99.88), ("42", 84.36, 54.34, 96.73),
                             ("1", 83.88, 64.69, 91.71)]],
    )  # fmt: skip
    corpo = client.get("/municipios/4202404/saneamento").json()
    assert corpo["ano"] == 2022
    assert corpo["cidade"]["esgoto_rede"] == 67.62
    assert corpo["estado"]["agua_rede"] == 84.36
    assert corpo["brasil"]["lixo_coletado"] == 91.71
    assert client.get("/municipios/9999999/saneamento").status_code == 404
