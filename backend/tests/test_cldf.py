from ingestion.assembleias import cldf


def test_autoria_em_texto_e_distribuicao():
    assert cldf.autores_de("Deputado Martins Machado, Deputado Martins Machado") == [
        "Martins Machado"
    ]
    assert cldf.nome_sem_titulo("Deputado João Cardoso ") == "João Cardoso"
    # Recortes reais da API do PLE (09/10/2026).
    props = [
        {"id": 159379, "tipoProposicao": "Requerimento", "siglaNumeroAno": "REQ 3090/2026",
         "dataLeitura": "2026-10-08", "autoria": "Deputado Martins Machado", "ementa": "Requer…"},
        {"id": 1, "tipoProposicao": "Projeto de Lei", "siglaNumeroAno": "PL 12/2026",
         "dataLeitura": "2026-02-03", "ementa": "Institui  o  Dia X.",
         "autoria": "Deputada Paula Belmonte, Deputado Martins Machado"},
        {"id": 2, "tipoProposicao": "Projeto de Lei", "siglaNumeroAno": "PL 13/2026",
         "dataLeitura": "2026-02-04", "ementa": "Y", "autoria": "Poder Executivo"},
    ]  # fmt: skip
    por = cldf.distribuir(props, {"Martins Machado", "Paula Belmonte"})
    assert por["Martins Machado"]["contagem"] == {"Requerimento": 1, "Projeto de Lei": 1}
    projeto = por["Paula Belmonte"]["projetos"][0]
    assert (projeto["numero"], projeto["ano"], projeto["primeiro_autor"]) == (12, 2026, True)
    assert projeto["ementa"] == "Institui o Dia X."
    assert por["Martins Machado"]["projetos"][0]["primeiro_autor"] is False
