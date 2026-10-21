"""Pauta do Plenário: GET /pauta."""

from datetime import date, timedelta

from app.models import PautaItem
from tests.helpers_projetos import ingestao, proposicao


def test_pauta_vazia_diz_o_fato(client, session):
    corpo = client.get("/pauta").json()
    assert corpo["itens"] == []
    assert corpo["dias"] == 14
    assert "Não há itens de pauta" in corpo["aviso"]
    assert corpo["atualizado_em"] is None
    assert corpo["fonte_nome"]


def test_pauta_por_data_com_link_quando_o_projeto_existe(client, session):
    hoje = date.today()
    ing = ingestao(session, "camara_pauta", hoje)
    proposicao(session, "100", "PL", 1, 2026, "Existe aqui.")
    for dia, sessao, ordem, pid, rotulo in [
        (hoje + timedelta(days=3), "s2", 1, "100", "PL 1/2026"),
        (hoje + timedelta(days=1), "s1", 2, "999", "PL 99/2026"),  # não existe aqui
        (hoje + timedelta(days=1), "s1", 1, "100", "PL 1/2026"),
        (hoje + timedelta(days=30), "s9", 1, "100", "PL 1/2026"),  # fora da janela de 14 dias
        (hoje - timedelta(days=2), "s0", 1, "100", "PL 1/2026"),  # já passou
    ]:
        session.add(
            PautaItem(
                casa="camara", data=dia, sessao=sessao, ordem=ordem, proposicao=rotulo,
                proposicao_id_externo=pid, ementa="Texto.", url="https://pauta",
                ingestao_id=ing.id,
            )
        )  # fmt: skip
    session.flush()
    corpo = client.get("/pauta?casa=camara").json()
    assert corpo["aviso"] is None
    assert [(i["data"], i["ordem"]) for i in corpo["itens"]] == [
        ((hoje + timedelta(days=1)).isoformat(), 1),
        ((hoje + timedelta(days=1)).isoformat(), 2),
        ((hoje + timedelta(days=3)).isoformat(), 1),
    ]
    assert [i["link"] for i in corpo["itens"]] == [
        "/projeto/camara/100",
        None,
        "/projeto/camara/100",
    ]
    assert corpo["itens"][0]["url_oficial"] == "https://pauta"
    assert corpo["atualizado_em"] is not None
    # Janela maior alcança o item de 30 dias.
    assert len(client.get("/pauta?casa=camara&dias=60").json()["itens"]) == 4


def test_pauta_filtra_a_casa_e_valida_parametros(client, session):
    hoje = date.today()
    ing = ingestao(session, "senado_pauta", hoje)
    session.add(PautaItem(casa="senado", data=hoje, sessao="1", proposicao="PEC 1/2025",
                          proposicao_id_externo="55", ingestao_id=ing.id))  # fmt: skip
    session.flush()
    assert len(client.get("/pauta").json()["itens"]) == 1
    assert client.get("/pauta?casa=camara").json()["itens"] == []
    assert client.get("/pauta?casa=senado").json()["itens"][0]["link"] is None
    assert client.get("/pauta?casa=stf").status_code == 422
    assert client.get("/pauta?dias=0").status_code == 422
    assert client.get("/pauta?dias=61").status_code == 422
