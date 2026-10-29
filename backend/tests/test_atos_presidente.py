"""MPV e vetos do Presidente: normalização (amostra real do Congresso), carga e API."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.models import AtoPresidencial, Candidatura, FonteIngestao
from app.services import atos_presidenciais
from ingestion.congresso import atos_presidente
from tests.conftest import carregar_fixture


@pytest.fixture
def amostra():
    return carregar_fixture("atos_presidente_amostra.json")


def _candidatura(session, sq, cargo, ano=2022, turno="ELEITO"):
    c = Candidatura(
        ano_eleicao=ano, sq_candidato=sq, cargo=cargo, uf="BR", unidade="Brasil",
        nome="Fulano de Tal", nome_urna="Fulano", titulo=f"00000000{sq}",
        situacao_turno=turno, genero="MASCULINO", partido="XX",
    )  # fmt: skip
    session.add(c)
    session.flush()
    return c


def _carregar(session, amostra):
    ing = FonteIngestao(
        fonte=atos_presidente.FONTE, url="x", arquivo_raw="x", status="ok",
        concluido_em=datetime.now(UTC),
    )  # fmt: skip
    session.add(ing)
    session.flush()
    linhas = atos_presidente.normalizar(amostra)
    atos_presidente.gravar(session, linhas, ing.id)
    session.flush()
    return linhas


def test_normalizar_fica_so_com_o_mandato_e_le_veto_total(amostra):
    linhas = atos_presidente.normalizar(amostra)
    ident = {r["identificacao"]: r for r in linhas}
    assert "MPV 1153/2022" not in ident  # editada em 30/12/2022: mandato anterior
    assert len(linhas) == 9
    assert ident["MPV 1154/2023"]["data"] == date(2023, 1, 1)
    assert ident["MPV 1287/2025"]["decisao"] == "PERDA_EFICACIA"
    assert ident["MPV 1287/2025"]["situacao"] == "SEM EFICÁCIA"
    assert ident["MPV 1287/2025"]["numero"] == 1287 and ident["MPV 1287/2025"]["ano"] == 2025
    assert (
        ident["MPV 1395/2026"]["tramitando"] is True and ident["MPV 1395/2026"]["decisao"] is None
    )
    assert ident["VET 8/2024"]["decisao"] == "REJEITADO_PLENARIO"
    assert ident["VET 8/2024"]["veto_total"] is False
    assert ident["VET 23/2024"]["veto_total"] is True and ident["VET 23/2024"]["tramitando"] is True
    assert ident["MPV 1287/2025"]["veto_total"] is None
    assert ident["MPV 1287/2025"]["url"].endswith("/mpv/166971")
    assert ident["VET 8/2024"]["url"].endswith(f"/detalhe/{ident['VET 8/2024']['id_externo']}")


def test_normalizar_ignora_repetido_e_sigla_trocada(amostra):
    amostra["mpv"] = amostra["mpv"] + [amostra["mpv"][0], {**amostra["veto"][0]}]
    assert len(atos_presidente.normalizar(amostra)) == 9


def test_grupos_de_leitura():
    g = atos_presidenciais.grupo_de
    assert g("mpv", "PERDA_EFICACIA", False) == "perdeu_eficacia"
    assert g("mpv", "APROVADO_PLV", False) == "aprovada"
    assert g("mpv", "REVOGADO", False) == "revogada"
    assert g("mpv", None, True) == "em_tramitacao"
    assert g("veto", None, True) == "pendente"
    assert g("veto", "REJEITADO_PLENARIO", False) == "derrubado"
    assert g("veto", "MANTIDA_MATE", False) == "mantido"
    assert g("veto", "MANTIDO_PARCIALMENTE", False) == "mantido_em_parte"
    assert g("veto", "PREJUDICADO", False) == "prejudicado"


def test_carga_e_idempotente(session, amostra):
    _carregar(session, amostra)
    _carregar(session, amostra)
    assert session.scalar(select(func.count()).select_from(AtoPresidencial)) == 9


def test_carga_vazia_aborta_e_nao_apaga(session, amostra):
    _carregar(session, amostra)
    ing = FonteIngestao(fonte=atos_presidente.FONTE, url="x", arquivo_raw="x")
    session.add(ing)
    session.flush()
    with pytest.raises(RuntimeError):
        atos_presidente.carregar(session, {"mpv": amostra["mpv"], "veto": []}, ing)
    assert session.scalar(select(func.count()).select_from(AtoPresidencial)) == 9


def test_carga_grava_e_conta(session, amostra):
    ing = FonteIngestao(fonte=atos_presidente.FONTE, url="x", arquivo_raw="x")
    session.add(ing)
    session.flush()
    assert atos_presidente.carregar(session, amostra, ing) == 9
    assert ing.total_fonte == 10  # a amostra traz também a MPV de 2022, que fica de fora


def test_painel_do_presidente_traz_mpv_e_vetos(client, session, amostra):
    _carregar(session, amostra)
    lula = _candidatura(session, "51", "PRESIDENTE")
    corpo = client.get(f"/executivo/{lula.id}/painel").json()
    mpv, vetos = corpo["medidas_provisorias"], corpo["vetos"]
    assert mpv["disponivel"] and mpv["atualizado_em"] is not None
    assert mpv["dados"]["total"] == 5
    assert mpv["dados"]["periodo"] == {"inicio": "2023-01-01", "fim": "2026-12-31"}
    por = {g["chave"]: g["quantidade"] for g in mpv["dados"]["grupos"]}
    assert por == {"em_tramitacao": 1, "aprovada": 1, "perdeu_eficacia": 2, "revogada": 1}
    assert mpv["rota"] == f"/executivo/{lula.id}/atos?tipo=mpv"
    pv = {g["chave"]: g["quantidade"] for g in vetos["dados"]["grupos"]}
    assert pv == {"derrubado": 1, "mantido_em_parte": 1, "mantido": 1, "pendente": 1}
    assert vetos["dados"]["total_integral"] == 1 and vetos["dados"]["total_parcial"] == 3


def test_vice_e_ex_presidente_nao_recebem_o_bloco(client, session, amostra):
    _carregar(session, amostra)
    vice = _candidatura(session, "52", "VICE-PRESIDENTE")
    antigo = _candidatura(session, "53", "PRESIDENTE", ano=2018)
    derrotado = _candidatura(session, "54", "PRESIDENTE", turno="NÃO ELEITO")
    for c in (vice, antigo, derrotado):
        corpo = client.get(f"/executivo/{c.id}/painel").json()
        assert corpo["medidas_provisorias"]["disponivel"] is False
        assert corpo["vetos"]["disponivel"] is False
        assert "mandato atual" in corpo["vetos"]["motivo"]
        assert client.get(f"/executivo/{c.id}/atos?tipo=mpv").status_code == 404


def test_lista_de_atos_com_filtro_e_pagina(client, session, amostra):
    _carregar(session, amostra)
    lula = _candidatura(session, "55", "PRESIDENTE")
    r = client.get(f"/executivo/{lula.id}/atos?tipo=mpv").json()
    assert r["total"] == 5
    assert [i["identificacao"] for i in r["itens"]][0] == "MPV 1395/2026"  # mais recente primeiro
    r = client.get(f"/executivo/{lula.id}/atos?tipo=mpv&grupo=perdeu_eficacia").json()
    assert r["total"] == 2 and all(i["termo_oficial"].startswith("Perdeu") for i in r["itens"])
    v = client.get(f"/executivo/{lula.id}/atos?tipo=veto&grupo=pendente").json()
    assert v["itens"][0]["veto"] == "Total" and v["itens"][0]["identificacao"] == "VET 23/2024"
    assert client.get(f"/executivo/{lula.id}/atos?tipo=veto&pagina=2").json()["itens"] == []
    assert client.get(f"/executivo/{lula.id}/atos?tipo=mpv&grupo=xx").status_code == 422
    assert client.get(f"/executivo/{lula.id}/atos?tipo=lei").status_code == 422


def test_sem_carga_diz_que_falta(client, session):
    lula = _candidatura(session, "56", "PRESIDENTE")
    corpo = client.get(f"/executivo/{lula.id}/painel").json()
    assert corpo["vetos"]["disponivel"] is False
    assert "ainda não foram carregadas" in corpo["vetos"]["motivo"]
