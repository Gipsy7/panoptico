from ingestion import comum
from ingestion.camara import etica


def test_nomes_na_ementa_reais():
    casos = {
        "Representação em desfavor do Senhor Deputado ZÉ TROVÃO por suposto procedimento "
        "incompatível com o decoro parlamentar.": ["ZÉ TROVÃO"],
        "Representa em desfavor do Senhor Deputado DELEGADO RAMAGEM, em razão de condenação "
        "criminal transitada em julgado.": ["DELEGADO RAMAGEM"],
        "Representação em desfavor do Senhor Deputado Gilvan da Federal, por procedimento "
        "incompatível com o decoro parlamentar.": ["Gilvan da Federal"],
        "Representação de autoria do Partido Novo em desfavor dos Senhores Deputados Chico "
        "Alencar, Glauber Braga e Ivan Valente, protocolizada em 1/1/2025.": [
            "Chico Alencar", "Glauber Braga", "Ivan Valente"],
    }  # fmt: skip
    for ementa, esperado in casos.items():
        assert etica.nomes_na_ementa(ementa) == esperado


def test_eventos_so_com_nome_unico_e_texto_oficial():
    deputados = {comum.chave_nome("Zé Trovão"): 10, comum.chave_nome("Ivan Valente"): 20}
    representacoes = [
        {"id": 1, "numero": 27, "ano": 2025, "dataApresentacao": "2025-09-23T11:31",
         "ementa": "Representação em desfavor do Senhor Deputado ZÉ TROVÃO por suposto "
                   "procedimento incompatível com o decoro parlamentar.",
         "statusProposicao": {"descricaoSituacao": "Tramitação Finalizada",
                              "descricaoTramitacao": "Apresentação de Recurso",
                              "dataHora": "2026-05-19T19:10"}},
        {"id": 2, "numero": 3, "ano": 2024, "dataApresentacao": "2024-01-02T10:00",
         "ementa": "Representação em desfavor do Senhor Deputado FULANO DE TAL, por x."},
    ]  # fmt: skip
    linhas, sem = etica.eventos(representacoes, deputados)
    assert sem == 1 and len(linhas) == 1 and linhas[0]["pessoa_id"] == 10
    assert linhas[0]["descricao"].startswith(
        'Representação nº 27/2025 no Conselho de Ética da Câmara: "Representação em desfavor'
    )
    assert linhas[0]["situacao"] == (
        "Tramitação Finalizada; último andamento em 19/05/2026: Apresentação de Recurso"
    )
