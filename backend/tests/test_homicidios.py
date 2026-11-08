"""Homicídios no SIM (DATASUS): leitura do DBF, recorte da CID, normalização e rota."""

import struct

import pytest
from sqlalchemy import insert

from app.models import HomicidioSim, Municipio, PopulacaoIbge
from ingestion.datasus import homicidios


def _dbf(caminho, registros):
    """DBF mínimo com as duas colunas lidas (CODMUNRES C7 e CAUSABAS C4) e uma extra no meio."""
    campos = [("CODMUNRES", 7), ("TIPOBITO", 1), ("CAUSABAS", 4)]
    tam_reg = 1 + sum(t for _, t in campos)
    tam_cab = 32 + 32 * len(campos) + 1
    cab = bytes([3, 124, 1, 1]) + struct.pack("<IHH", len(registros), tam_cab, tam_reg) + bytes(20)
    descr = b"".join(
        n.encode().ljust(11, b"\0") + b"C" + bytes(4) + bytes([t, 0]) + bytes(14) for n, t in campos
    )
    corpo = b"".join(
        (b"*" if apagado else b" ") + mun.ljust(7).encode() + b"2" + causa.ljust(4).encode()
        for mun, causa, apagado in registros
    )
    caminho.write_bytes(cab + descr + b"\r" + corpo + b"\x1a")


def test_recorte_da_cid():
    assert homicidios.e_homicidio("X954")
    assert homicidios.e_homicidio("Y09")
    assert homicidios.e_homicidio("Y350")
    assert not homicidios.e_homicidio("X849")  # lesão autoprovocada: fora
    assert not homicidios.e_homicidio("Y10")  # intenção indeterminada: fora
    assert not homicidios.e_homicidio("I219")


def test_ler_dbf_conta_por_municipio_e_ignora_apagados(tmp_path):
    arq = tmp_path / "DOSC2024.dbf"
    _dbf(
        arq,
        [("420240", "X954", False), ("420240", "Y350", False), ("420240", "I219", False),
         ("420000", "X999", False), ("420910", "X954", True)],
    )  # fmt: skip
    por_mun, total = homicidios.ler_dbf(arq)
    assert por_mun == {"420240": 2, "420000": 1}
    assert total == 3


def test_normalizar_zera_cidade_sem_caso_e_pula_ano_incompleto():
    ufs = {uf: 1 for uf in homicidios.CODIGO_UF}
    recorte = {
        "anos": {
            "2024": {"uf": ufs, "municipios": {"420240": 20, "420000": 3}},
            "2025": {"uf": {"SC": 5}, "municipios": {"420240": 5}},
        }
    }
    mapa6 = {"420240": "4202404", "420910": "4209102"}
    linhas = {
        (r["codigo"], r["ano"]): r["homicidios"] for r in homicidios.normalizar(recorte, mapa6)
    }
    assert linhas[("4202404", 2024)] == 20
    assert linhas[("4209102", 2024)] == 0
    assert linhas[("1", 2024)] == 27
    assert not any(ano == 2025 for _, ano in linhas)


def test_carregar_aborta_sem_ano_completo(session):
    with pytest.raises(ValueError):
        homicidios.carregar(session, {"anos": {}}, type("I", (), {"id": None})())


def test_rota_da_seguranca(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(HomicidioSim),
        [{"codigo": c, "ano": a, "homicidios": n}
         for c, base in [("4202404", 20), ("42", 650), ("1", 40000)]
         for a, n in [(2022, base), (2023, base), (2024, base)]],
    )  # fmt: skip
    session.execute(
        insert(PopulacaoIbge),
        [{"codigo": c, "ano": 2022, "valor": v, "origem": "censo"}
         for c, v in [("4202404", 400000), ("42", 8000000), ("1", 200000000)]],
    )  # fmt: skip
    corpo = client.get("/municipios/4202404/seguranca").json()
    assert [p["ano"] for p in corpo["cidade"]["serie"]] == [2022, 2023, 2024]
    assert corpo["cidade"]["serie"][-1]["por_100_mil"] == pytest.approx(5.0)
    assert corpo["cidade"]["media_3_anos_por_100_mil"] == pytest.approx(5.0)
    assert corpo["estado"]["serie"][-1]["homicidios"] == 650
    assert corpo["brasil"]["media_3_anos_por_100_mil"] == pytest.approx(20.0)
    assert client.get("/municipios/9999999/seguranca").status_code == 404
