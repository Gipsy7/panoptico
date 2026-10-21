"""Votação e projeto de câmara municipal ou assembleia: o que a casa publica."""

from datetime import date

from tests.helpers_projetos import ingestao, mandato_local, projeto_local, votacao_local


def test_votacao_local_com_materia_e_votos(client, session):
    ana = mandato_local(session, "Ana", "camara", partido="PXX")
    bia = mandato_local(session, "Bia", "camara", partido="PYY")
    caio = mandato_local(session, "Caio", "camara", partido="PXX")
    projeto = projeto_local(session, ana)
    ingestao(session, "sapl_camaras", date(2026, 10, 19))
    v = votacao_local(
        session, "camara", "SC", materia="Projeto de Lei nº 7/2026",
        materia_ementa="Institui a semana da saúde mental.", projeto_local_id=projeto.id,
        votos={ana.id: "Sim", bia.id: "Não", caio.id: "Abstenção"},
    )  # fmt: skip
    corpo = client.get(f"/votacoes/local/{v.id}").json()
    assert corpo["casa"] == "camara_municipal"
    assert corpo["municipio"] == "Florianópolis"
    assert corpo["uf"] == "SC"
    assert corpo["materia"] == "Projeto de Lei nº 7/2026"
    assert corpo["ementa"] == "Institui a semana da saúde mental."
    assert (corpo["resultado"], corpo["sim"], corpo["nao"]) == ("Aprovado", 8, 2)
    assert [(x["nome"], x["voto"]) for x in corpo["votos"]] == [
        ("Ana", "Sim"),
        ("Bia", "Não"),
        ("Caio", "Abstenção"),
    ]
    assert corpo["votos"][0]["partido"] == "PXX"
    assert corpo["projeto_link"] == f"/projeto/local/{projeto.id}"
    assert corpo["url_oficial"] == "https://camara.exemplo/votacao/1"
    assert corpo["sem_orientacao"] is True
    assert corpo["sem_discursos"] is True
    assert "não publica orientação de bancada nem discursos" in corpo["aviso"]
    assert "ementa" not in corpo["aviso"]
    assert corpo["fonte_url"] == "https://camara.exemplo/votacao/1"
    assert corpo["atualizado_em"].startswith("2026-10-19")


def test_votacao_local_sem_materia_ligada_nem_ementa(client, session):
    ana = mandato_local(session, "Ana", "assembleia", "AC")
    v = votacao_local(session, "assembleia", "AC", materia="Veto nº 4 de 2026",
                      votos={ana.id: "Sim"})  # fmt: skip
    corpo = client.get(f"/votacoes/local/{v.id}").json()
    assert corpo["casa"] == "assembleia"
    assert corpo["municipio"] is None
    assert corpo["ementa"] is None
    assert corpo["projeto_local_id"] is None
    assert corpo["projeto_link"] is None
    assert "não publica a ementa" in corpo["aviso"]
    assert corpo["atualizado_em"] is None


def test_votacao_local_inexistente(client, session):
    assert client.get("/votacoes/local/999999").status_code == 404
    # Rota federal continua no formato antigo.
    assert client.get("/votacoes/camara/nao-existe").status_code == 404


def test_projeto_local_lista_as_votacoes_ligadas(client, session):
    ana = mandato_local(session, "Ana", "camara", partido="PXX")
    projeto = projeto_local(session, ana, "Projeto de Lei Ordinária", 7, 2026)
    primeira = votacao_local(
        session,
        "camara",
        "SC",
        data=date(2026, 8, 1),
        materia="PL 7/2026 - 1º turno",
        projeto_local_id=projeto.id,
    )
    segunda = votacao_local(
        session, "camara", "SC", data=date(2026, 9, 1), resultado="Rejeitado",
        materia="PL 7/2026 - 2º turno", projeto_local_id=projeto.id,
    )  # fmt: skip
    votacao_local(session, "camara", "SC", materia="Outra, sem vínculo")
    corpo = client.get(f"/projetos/local/{projeto.id}").json()
    assert corpo["rotulo"] == "Projeto de Lei Ordinária nº 7/2026"
    assert corpo["ementa"] == "Institui a semana da saúde mental."
    assert corpo["casa"] == "camara_municipal"
    assert corpo["municipio"] == "Florianópolis"
    assert corpo["autor"] == {"mandato_id": ana.id, "nome": "Ana", "partido": "PXX"}
    assert corpo["em_tramitacao"] is True
    assert [v["id"] for v in corpo["votacoes"]] == [segunda.id, primeira.id]
    assert corpo["votacoes"][0]["link"] == f"/votacoes/local/{segunda.id}"
    assert corpo["votacoes"][0]["resultado"] == "Rejeitado"
    assert corpo["sem_orientacao"] is True and corpo["sem_discursos"] is True
    assert corpo["url_oficial"] == "https://camara.exemplo/projeto/1"
    assert "simbólica" not in corpo["aviso"]


def test_projeto_local_sem_votacao_nominal(client, session):
    ana = mandato_local(session, "Ana", "assembleia", "AC")
    projeto = projeto_local(session, ana, "Proposta de Emenda", 1, 2026, "Altera algo.")
    corpo = client.get(f"/projetos/local/{projeto.id}").json()
    assert corpo["votacoes"] == []
    assert corpo["casa"] == "assembleia"
    assert corpo["municipio"] is None
    assert "simbólica" in corpo["aviso"]
    assert client.get("/projetos/local/999999").status_code == 404
