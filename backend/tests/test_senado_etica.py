from ingestion import comum
from ingestion.senado import etica


def test_representacao_do_senado():
    # Registro real da rota /processo do Senado (09/10/2026).
    rep = {"id": 1, "codigoMateria": 158000, "identificacao": "REP 1/2024",
           "dataApresentacao": "2024-07-09", "autoria": "Partido Socialismo e Liberdade",
           "situacaoAtual": "TRAMITAÇÃO ENCERRADA",
           "ementa": "Requer a abertura de procedimento disciplinar (Representação) em face do "
                     "Senador Flávio Bolsonaro, com fundamento no art. 55, II"}  # fmt: skip
    linhas, sem = etica.eventos([rep], {comum.chave_nome("Flávio Bolsonaro"): 7})
    assert sem == 0 and linhas[0]["pessoa_id"] == 7
    assert linhas[0]["descricao"].startswith(
        "REP 1/2024 no Conselho de Ética do Senado, de autoria de Partido Socialismo e Liberdade"
    )
    assert linhas[0]["situacao"] == "Tramitação encerrada"
