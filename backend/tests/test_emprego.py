"""CEMPRE do IBGE: valores reais de Blumenau (tabelas 9509 e 9510, 08/11/2026)."""

from decimal import Decimal

import pytest
from sqlalchemy import insert

from app.models import EmpregoIbge, EmpregoSetor, Municipio
from ingestion.ibge import cempre


def _recorte() -> dict:
    return {
        "ano_setores": 2024,
        "totais": {
            "2024:707": {"4202404": "198372", "1": "198372"},
            "2024:708": {"4202404": "147817", "1": "X"},
            "2024:10143": {"4202404": "4069.10"},
            "2024:367": {"4202404": "36264"},
        },
        "setores": {
            "C Indústrias de transformação": {"4202404": "47410"},
            "A Agricultura, pecuária, produção florestal, pesca e aquicultura": {"4202404": "X"},
        },
    }


def test_normalizar_guarda_totais_e_secoes_sem_sigilo():
    totais, setores = cempre.normalizar(_recorte())
    b = next(r for r in totais if r["codigo"] == "4202404")
    assert b["pessoal_ocupado"] == Decimal(198372)
    assert b["salario_medio"] == Decimal("4069.10")
    br = next(r for r in totais if r["codigo"] == "1")
    assert br["assalariados"] is None  # "X" é sigilo
    assert [(s["secao"], s["nome"]) for s in setores] == [("C", "Indústrias de transformação")]
    cempre.conferir(totais)


def test_conferir_fecha_com_o_brasil():
    with pytest.raises(ValueError):
        cempre.conferir(
            [
                {"codigo": "1", "ano": 2024, "pessoal_ocupado": Decimal(10)},
                {"codigo": "4202404", "ano": 2024, "pessoal_ocupado": Decimal(5)},
            ]
        )


def test_rota_do_emprego(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    session.execute(
        insert(EmpregoIbge),
        [
            {
                "codigo": "4202404",
                "ano": 2024,
                "pessoal_ocupado": 198372,
                "salario_medio": 4069.10,
                "salario_medio_sm": 2.9,
                "empresas": 36264,
                "assalariados": 147817,
            },
            {"codigo": "42", "ano": 2024, "pessoal_ocupado": 3000000, "salario_medio": 3800},
            {"codigo": "1", "ano": 2024, "pessoal_ocupado": 60000000, "salario_medio": 3600},
        ],
    )
    session.execute(
        insert(EmpregoSetor),
        [
            {
                "codigo": "4202404",
                "ano": 2024,
                "secao": "C",
                "nome": "Indústrias de transformação",
                "pessoal_ocupado": 47410,
            },
            {
                "codigo": "4202404",
                "ano": 2024,
                "secao": "G",
                "nome": "Comércio",
                "pessoal_ocupado": 39364,
            },
        ],
    )
    corpo = client.get("/municipios/4202404/emprego").json()
    a = corpo["serie"][0]
    assert a["salario_medio"] == 4069.10
    assert a["uf_salario_medio"] == 3800
    assert a["brasil_salario_medio"] == 3600
    assert [s["secao"] for s in corpo["setores"]] == ["C", "G"]
    assert round(corpo["setores"][0]["percentual"], 1) == round(100 * 47410 / (47410 + 39364), 1)
    assert client.get("/municipios/9999999/emprego").status_code == 404
