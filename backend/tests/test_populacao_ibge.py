import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import FonteIngestao, PopulacaoIbge
from ingestion.ibge import populacao as pop

AMOSTRA = json.loads(
    (Path(__file__).parent / "fixtures" / "ibge_populacao_amostra.json").read_text("utf-8")
)


def _linha(codigo, valor, ano=2024):
    return {"V": valor, "D1C": codigo, "D1N": "x", "D3C": str(ano)}


def _payload(brasil=10, ufs=(4, 6), municipios=(3, 3, 4), ano=2024):
    cab = [{"V": "Valor", "D1C": "Cód"}]
    return {
        f"n1_{ano}": cab + [_linha("1", str(brasil), ano)],
        f"n3_{ano}": cab + [_linha(f"1{i}", str(v), ano) for i, v in enumerate(ufs, 1)],
        f"n6_{ano}": cab + [_linha(f"110000{i}", str(v), ano) for i, v in enumerate(municipios, 1)],
    }


def test_normalizar_amostra_real_pula_cabecalho_e_marca_origem():
    registros = pop.normalizar(AMOSTRA)
    por_chave = {(r["codigo"], r["ano"]): r for r in registros}
    assert por_chave[("1", 2024)] == {
        "codigo": "1", "ano": 2024, "valor": 212583750, "origem": "estimativa"
    }  # fmt: skip
    assert por_chave[("1", 2022)]["origem"] == "censo"
    assert por_chave[("1", 2022)]["valor"] == 203080756
    assert len(registros) == 6  # n1 (1), n3 (2) e n6 (2) de 2024, e o n1 do Censo 2022


def test_valor_ausente_nao_e_guardado():
    payload = _payload()
    payload["n6_2024"].append(_linha("1100009", "..."))
    assert all(r["codigo"] != "1100009" for r in pop.normalizar(payload))


def test_conferir_soma_das_ufs_e_municipios():
    pop.conferir(pop.normalizar(_payload()))
    with pytest.raises(ValueError):
        pop.conferir(pop.normalizar(_payload(ufs=(4, 5))))
    with pytest.raises(ValueError):
        pop.conferir(pop.normalizar(_payload(municipios=(3, 3, 3))))


def test_url_do_censo_e_da_estimativa():
    assert pop.url("n6", 2024) == "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2024"
    assert "/t/9514/n1/all/v/93/p/2022/" in pop.url("n1", 2022)


def test_carregar_idempotente_e_sem_2023(session):
    ingestao = FonteIngestao(fonte=pop.FONTE, url=pop.BASE, arquivo_raw="x")
    session.add(ingestao)
    session.flush()
    session.add(PopulacaoIbge(codigo="1", ano=2023, valor=1, origem="estimativa"))
    session.flush()
    assert pop.carregar(session, _payload(), ingestao) == 6
    assert pop.carregar(session, _payload(), ingestao) == 6
    anos = set(session.scalars(select(PopulacaoIbge.ano)))
    assert anos == {2023, 2024}  # só reinsere os anos recebidos; nada é inventado


def test_carregar_aborta_se_nao_fecha_ou_vazio(session):
    ingestao = FonteIngestao(fonte=pop.FONTE, url=pop.BASE, arquivo_raw="x")
    session.add(ingestao)
    session.flush()
    with pytest.raises(ValueError):
        pop.carregar(session, {}, ingestao)
    with pytest.raises(ValueError):
        pop.carregar(session, _payload(ufs=(1, 1)), ingestao)
