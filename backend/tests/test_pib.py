"""PIB dos Municípios (IBGE): valores reais de Blumenau (API v3 do SIDRA, 08/11/2026)."""

from decimal import Decimal

import pytest
from sqlalchemy import insert

from app.models import Municipio, PibIbge, PopulacaoIbge
from ingestion.ibge import pib
from tests.test_api import _ingestao

SEIS = ["37", "498", "513", "517", "6575", "525"]


def _recorte(ano: int, mun: list[str], uf: list[str], br: list[str]) -> dict:
    return {
        f"N6_{ano}": {v: {"4202404": x} for v, x in zip(SEIS, mun, strict=True)},
        f"N3_{ano}": {v: {"42": x} for v, x in zip(SEIS, uf, strict=True)},
        f"N1_{ano}": {v: {"1": x} for v, x in zip(SEIS, br, strict=True)},
    }


def test_normalizar_guarda_setores_e_deixa_vazio_o_que_falta():
    rec = _recorte(2021, ["20579490", "17395077", "120512", "4729190", "10521313", "2024063"],
                   ["1"] * 6, ["2"] * 6)  # fmt: skip
    rec |= _recorte(2023, ["24871920", "...", "...", "...", "...", "..."], ["1"] * 6, ["2"] * 6)
    linhas = {(r["codigo"], r["ano"]): r for r in pib.normalizar(rec)}
    b21 = linhas[("4202404", 2021)]
    assert b21["pib"] == Decimal("20579490") and b21["vab_industria"] == Decimal("4729190")
    b23 = linhas[("4202404", 2023)]
    assert b23["pib"] == Decimal("24871920") and b23["vab_total"] is None


def test_conferir_soma_dos_municipios_com_o_brasil():
    ok = [{"codigo": "1", "ano": 2021, "pib": Decimal(1000)},
          {"codigo": "4202404", "ano": 2021, "pib": Decimal(998)}]  # fmt: skip
    pib.conferir(ok)
    with pytest.raises(ValueError):
        pib.conferir([ok[0], {**ok[1], "pib": Decimal(900)}])


def test_carga_aborta_com_poucos_municipios(session):
    rec = _recorte(2021, ["1"] * 6, ["1"] * 6, ["1"] * 6)
    with pytest.raises(ValueError):
        pib.carregar(session, rec, _ingestao(session, pib.FONTE))


def test_rota_do_pib_com_por_morador_do_estado_e_do_brasil(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(PibIbge),
        [
            {"codigo": "4202404", "ano": 2021, "pib": 20579490, "vab_total": 17395077,
             "vab_agropecuaria": 120512, "vab_industria": 4729190, "vab_servicos": 10521313,
             "vab_administracao": 2024063},
            {"codigo": "42", "ano": 2021, "pib": 428570000},
            {"codigo": "1", "ano": 2021, "pib": 9012142000},
            {"codigo": "4202404", "ano": 2023, "pib": 24871920},
        ],
    )  # fmt: skip
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": "4202404", "ano": 2021, "valor": 366418, "origem": "estimativa"},
         {"codigo": "42", "ano": 2021, "valor": 7338473, "origem": "estimativa"},
         {"codigo": "1", "ano": 2021, "valor": 213317639, "origem": "estimativa"}],
    )  # fmt: skip
    corpo = client.get("/municipios/4202404/pib").json()
    a21, a23 = corpo["serie"]
    assert round(a21["por_habitante"]) == round(20579490 * 1000 / 366418)
    assert round(a21["uf_por_habitante"]) == round(428570000 * 1000 / 7338473)
    assert a23["por_habitante"] is None  # 2023 sem população do IBGE: não se inventa
    assert corpo["setores"]["ano"] == 2021
    industria = next(s for s in corpo["setores"]["itens"] if s["setor"] == "Indústria")
    assert round(industria["percentual"], 1) == round(100 * 4729190 / 17395077, 1)
    assert client.get("/municipios/9999999/pib").status_code == 404
