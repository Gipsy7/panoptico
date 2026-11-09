"""Placar oficial da Câmara lido da descrição quando votosSim/votosNao vêm vazios."""

from ingestion.camara.votacoes import placar_da_descricao


def test_placar_lido_da_descricao_quando_a_camara_nao_preenche():
    d = "Aprovada a Subemenda ao PLP 74, de 2026. Sim: 346; Não: 46; Abstenção: 3; Total: 395."
    assert placar_da_descricao(d) == {"placar_sim": 346, "placar_nao": 46, "placar_abstencao": 3}
    assert placar_da_descricao("Sim: 10; Nao: 2") == {
        "placar_sim": 10,
        "placar_nao": 2,
        "placar_abstencao": None,
    }
    assert placar_da_descricao("Aprovado o requerimento.") == {}
