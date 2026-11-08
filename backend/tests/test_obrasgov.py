"""Obras federais do Obrasgov.br: amostras reais da API pública (08/11/2026), recortadas."""

import json
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Municipio, ObraFederal, ObraFederalMunicipio
from ingestion.obrasgov import obras
from tests.test_api import _ingestao


def _projeto(id_, nome, situacao, valor, uf="SC", fonte="Federal"):
    return {
        "id_projeto_investimento": id_,
        "desc_nome": nome,
        "situacao": situacao,
        "natureza_intervencao": "Obra",
        "especie_intervencao": "Construção",
        "uf_principal": uf,
        "dt_inicial_prevista": "2025-06-09",
        "dt_final_prevista": "2029-06-09",
        "dt_inicial_efetiva": None,
        "dt_final_efetiva": None,
        "dt_cadastro": "2025-06-09",
        "organizacao_resp": "MINISTÉRIO DA INTEGRAÇÃO E DO DESENVOLVIMENTO REGIONAL",
        "executores": [
            {"organizacao_executor": "MUNICIPIO DE RIO NEGRINHO", "cnpj_executor": "83102756000179"}
        ],
        "investimentos_previstos": [
            {"vl_investimento_previsto": valor, "desc_nome_fonte_recurso": fonte}
        ],
        "eixos_tipos": [
            {
                "eixo": "Social",
                "tipo": "Infraestrutura Urbana e Mobilidade",
                "subtipo": "Urbanização",
            }
        ],
    }


RECORTE = {
    "projetos": [
        _projeto("60666.42-52", "PAVIMENTAÇÃO SC 112 SERRO AZUL 2,2KM", "Cadastrada", 5000000.0),
        _projeto("151020.43-16", "IMPLANTACAO UBS", "Em execução", 200000.0, uf="RS"),
        # A mesma obra em duas páginas (a API não ordena): fica uma só.
        _projeto("151020.43-16", "IMPLANTACAO UBS", "Em execução", 200000.0, uf="RS"),
        {
            **_projeto("14449.42-17", "QUADRA", "Paralisada", 100.0, fonte="Estadual"),
            "investimentos_previstos": [
                {"vl_investimento_previsto": 300000.0, "desc_nome_fonte_recurso": "Federal"},
                {"vl_investimento_previsto": 50000.5, "desc_nome_fonte_recurso": "Estadual"},
            ],
        },  # fmt: skip
        {**_projeto("sem-nome", "", "Cadastrada", 1.0)},
    ],
    "geometrias": [
        {"id_projeto_investimento": "60666.42-52", "cod_ibge": 4214805},
        {"id_projeto_investimento": "151020.43-16", "cod_ibge": 4319372},
        # Duas geometrias na mesma cidade e uma em outra: duas ligações.
        {"id_projeto_investimento": "14449.42-17", "cod_ibge": 4202404},
        {"id_projeto_investimento": "14449.42-17", "cod_ibge": 4202404},
        {"id_projeto_investimento": "14449.42-17", "cod_ibge": 4214805},
        {"id_projeto_investimento": "id-que-nao-existe", "cod_ibge": 4202404},
        {"id_projeto_investimento": "60666.42-52", "cod_ibge": None},
    ],
    "execucoes": [
        {
            "id_projeto_investimento": "14449.42-17",
            "percentual_execucao_fisica": 40.0,
            "dt_atualizacao_execucao": "2025-01-10",
        },
        {
            "id_projeto_investimento": "14449.42-17",
            "percentual_execucao_fisica": 62.5,
            "dt_atualizacao_execucao": "2026-10-21",
        },
    ],
}


def test_normalizar_junta_paginas_soma_fontes_e_pega_a_execucao_mais_recente():
    lista, municipios = obras.normalizar(RECORTE)
    por_id = {o["id_unico"]: o for o in lista}
    assert set(por_id) == {"60666.42-52", "151020.43-16", "14449.42-17"}  # sem nome fica fora
    quadra = por_id["14449.42-17"]
    assert quadra["valor_previsto"] == Decimal("350000.5")
    assert quadra["valor_previsto_federal"] == Decimal("300000.0")
    assert quadra["percentual_execucao"] == Decimal("62.5")
    assert str(quadra["execucao_atualizada_em"]) == "2026-10-21"
    assert por_id["60666.42-52"]["percentual_execucao"] is None
    assert por_id["60666.42-52"]["tipo"] == "Infraestrutura Urbana e Mobilidade"
    assert {(m["obra_id"], m["municipio_ibge"]) for m in municipios} == {
        ("60666.42-52", "4214805"),
        ("151020.43-16", "4319372"),
        ("14449.42-17", "4202404"),
        ("14449.42-17", "4214805"),
    }


def test_carga_idempotente_e_aborta_sem_obras(session):
    payload = json.dumps(RECORTE).encode()
    assert obras.carregar(session, payload, _ingestao(session, obras.FONTE)) == 3
    assert obras.carregar(session, payload, _ingestao(session, obras.FONTE)) == 3
    assert session.scalar(select(func.count()).select_from(ObraFederal)) == 3
    assert session.scalar(select(func.count()).select_from(ObraFederalMunicipio)) == 4
    with pytest.raises(ValueError):
        obras.carregar(
            session,
            json.dumps({"projetos": [], "geometrias": [], "execucoes": []}).encode(),
            _ingestao(session, obras.FONTE),
        )


def test_rota_das_obras_da_cidade(client, session):
    session.add(Municipio(ibge="4214805", nome="Rio Negrinho", uf="SC", nome_chave="RIO NEGRINHO"))
    session.flush()
    obras.carregar(session, json.dumps(RECORTE).encode(), _ingestao(session, obras.FONTE))
    corpo = client.get("/municipios/4214805/obras").json()
    assert corpo["total"] == 2
    # Em andamento ou parada vem antes de cadastrada.
    assert [i["situacao"] for i in corpo["itens"]] == ["Paralisada", "Cadastrada"]
    assert [g["situacao"] for g in corpo["por_situacao"]] == ["Paralisada", "Cadastrada"]
    assert float(corpo["valor_previsto"]) == 5350000.5
    assert corpo["itens"][0]["url"].endswith("id_projeto_investimento=14449.42-17")
    assert client.get("/municipios/9999999/obras").status_code == 404


def test_rota_das_obras_por_estado(client, session):
    obras.carregar(session, json.dumps(RECORTE).encode(), _ingestao(session, obras.FONTE))
    corpo = client.get("/obras/estados").json()
    sc = next(u for u in corpo["ufs"] if u["uf"] == "SC")
    assert sc["total"] == 2
    assert [g["situacao"] for g in sc["por_situacao"]] == ["Paralisada", "Cadastrada"]
