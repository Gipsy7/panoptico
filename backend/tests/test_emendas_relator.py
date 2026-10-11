from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import EmendaRelatorIndicacao, Parlamentar
from ingestion.congresso import emendas_relator as rp9
from tests.test_api import _ingestao

# Recorte real da planilha consolidada da CMO (LOA 2022): dois pedidos de um deputado, um de
# um senador, um de deputado fora da base, um de usuário externo e uma linha repetida.
PLANILHA = (Path(__file__).parent / "fixtures" / "emendas_relator_recorte.xlsx").read_bytes()


def _novo(session, casa: str, id_externo: str, nome: str, civil: str | None = None):
    p = Parlamentar(
        casa=casa,
        id_externo=id_externo,
        nome_parlamentar=nome,
        nome_civil=civil,
        uf="BA",
        em_exercicio=True,
        fonte_url="https://exemplo",
        atualizado_em=date(2026, 1, 1),
    )
    session.add(p)
    session.flush()
    return p


def test_normalizar_so_parlamentares_e_sem_repetidas():
    registros = rp9.normalizar(PLANILHA)
    assert [r["numero"] for r in registros] == [42789, 42792, 1472, 23481]
    primeiro = registros[0]
    assert primeiro["casa"] == "camara"
    assert primeiro["beneficiario"] == "FUNDO MUNICIPAL DE SAÚDE DE NOVA ITARANA"
    assert primeiro["beneficiario_cnpj"] == "12420226000120"
    assert primeiro["valor_solicitado"] == Decimal("1000000")
    assert primeiro["data_cadastro"] == date(2022, 6, 1)
    assert registros[2]["casa"] == "senado"


def test_vincular_exato_na_mesma_casa_e_fora_da_base():
    registros = rp9.normalizar(PLANILHA)
    base = [
        (1, "camara", "Abílio Santana", None),
        (2, "senado", "Luis Carlos Heinze", "Luis Carlos Heinze"),
        (3, "camara", "Luis Carlos Heinze", None),  # mesmo nome, outra Casa: não vale
    ]
    ligadas, fora = rp9.vincular(registros, base)
    assert [(r["numero"], r["parlamentar_id"]) for r in ligadas] == [
        (42789, 1),
        (42792, 1),
        (1472, 2),
    ]
    assert fora == {"fora_da_base": 1, "ambiguo": 0}


def test_vincular_nome_ambiguo_nao_liga():
    registros = rp9.normalizar(PLANILHA)[:1]
    base = [(1, "camara", "Abilio Santana", None), (2, "camara", "Outro", "Abilio Santana")]
    ligadas, fora = rp9.vincular(registros, base)
    assert ligadas == [] and fora["ambiguo"] == 1


def test_carregar_idempotente_e_aborta_sem_indicacao(session):
    abilio = _novo(session, "camara", "900001", "Abílio Santana")
    ing = _ingestao(session, rp9.FONTE)
    assert rp9.carregar(session, PLANILHA, ing) == 2
    assert rp9.carregar(session, PLANILHA, ing) == 2
    linhas = session.scalars(select(EmendaRelatorIndicacao)).all()
    assert len(linhas) == 2 and {i.parlamentar_id for i in linhas} == {abilio.id}
    # Sem parlamentar da base, nada é ligado: aborta e mantém o que havia.
    session.execute(Parlamentar.__table__.update().values(nome_parlamentar="Fulano"))
    with pytest.raises(ValueError):
        rp9.carregar(session, PLANILHA, ing)
    assert len(session.scalars(select(EmendaRelatorIndicacao)).all()) == 2


def test_api_indicacoes_do_parlamentar(session, client):
    abilio = _novo(session, "camara", "900001", "Abílio Santana")
    sem = _novo(session, "camara", "900002", "Outro Deputado")
    ing = _ingestao(session, rp9.FONTE)
    rp9.carregar(session, PLANILHA, ing)
    session.commit()
    r = client.get(f"/parlamentares/{abilio.id}/emendas-relator")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["quantidade"] == 2 and corpo["valor_solicitado"] == 2000000
    assert corpo["beneficiarios"] == 2 and corpo["ano"] == 2022
    assert corpo["por_orgao"][0]["orgao"] == "Ministerio Da Saude"
    assert corpo["itens"][0]["beneficiario"].startswith("FUNDO MUNICIPAL DE SAÚDE")
    assert client.get(f"/parlamentares/{sem.id}/emendas-relator").status_code == 404
