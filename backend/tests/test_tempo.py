"""Linha do tempo do lugar: IPCA (reais do último ano completo), gasto por morador e rotas."""

from decimal import Decimal

import pytest
from sqlalchemy import insert

from app.models import ContasEstado, ContasMunicipio, IpcaIndice, Municipio
from app.services import tempo
from ingestion.ibge import ipca


def _ipca(session, por_ano: dict[int, float], meses=12):
    session.execute(
        insert(IpcaIndice),
        [{"ano": a, "mes": m, "indice": Decimal(str(v))} for a, v in por_ano.items()
         for m in range(1, meses + 1)],
    )  # fmt: skip


def test_normalizar_ipca_pula_vazios():
    payload = [{"resultados": [{"series": [{"serie": {"202401": "7000.1", "202402": "..."}}]}]}]
    assert ipca.normalizar(payload) == [{"ano": 2024, "mes": 1, "indice": Decimal("7000.1")}]


def test_fatores_usam_o_ultimo_ano_completo(session):
    _ipca(session, {2015: 100.0, 2024: 200.0})
    _ipca(session, {2025: 400.0}, meses=3)  # incompleto: não vira referência
    ref, fat = tempo.fatores_ipca(session)
    assert ref == 2024
    assert fat[2015] == pytest.approx(2.0)
    assert fat[2024] == pytest.approx(1.0)


def test_rota_tempo_da_cidade_e_do_estado(client, session):
    session.add(Municipio(ibge="4205902", nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.flush()
    _ipca(session, {2015: 100.0, 2024: 200.0})
    session.add(
        ContasMunicipio(
            municipio_ibge="4205902",
            ano=2015,
            populacao=50000,
            despesa_por_area={"Saúde": 5_000_000},
        )
    )
    session.add(
        ContasMunicipio(
            municipio_ibge="4205902",
            ano=2024,
            populacao=70000,
            despesa_por_area={"Saúde": 14_000_000},
        )
    )
    session.add(ContasEstado(uf="SC", ano=2015, populacao=7_000_000,
                             despesa_por_area={"Segurança Pública": 1_400_000_000}))  # fmt: skip
    session.flush()
    corpo = client.get("/municipios/4205902/tempo").json()
    assert corpo["reais_de"] == 2024
    por = {s["id"]: s for s in corpo["series"]}
    saude = por["gasto_saude_prefeitura"]["pontos"]
    assert saude == [{"ano": 2015, "valor": 200.0}, {"ano": 2024, "valor": 200.0}]
    assert por["gasto_seguranca_estado"]["pontos"][0]["valor"] == pytest.approx(400.0)
    assert "gasto_educacao_prefeitura" not in por  # sem pontos: fora
    uf = client.get("/estados/sc/tempo").json()
    assert "gasto_seguranca_estado" in {s["id"] for s in uf["series"]}
    assert client.get("/municipios/9999999/tempo").status_code == 404
