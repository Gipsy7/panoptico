import httpx

from ingestion import comum
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO, TEMA_HOMENAGENS
from ingestion.senado import temas
from ingestion.senado import votacoes as senado


def test_tema_da_classificacao_usa_o_segundo_nivel():
    assert temas.tema_da_classificacao("Política Social / Educação / Educação Básica") == "Educação"
    assert temas.tema_da_classificacao("Jurídico / Direito Penal e Penitenciário") == (
        "Direito Penal e Penitenciário"
    )
    assert temas.tema_da_classificacao("Orçamento Público") == "Orçamento Público"
    assert temas.tema_da_classificacao("Honorífico / Homenagem") == TEMA_HOMENAGENS
    assert temas.tema_da_classificacao("") == SEM_CLASSIFICACAO


def test_normalizar_temas_do_senado():
    payload = {
        "157013": [
            {"descricaoHierarquia": "Política Social / Educação / Educação Básica"},
            {"descricaoHierarquia": "Política Social / Educação / Ensino Superior"},
            {"descricaoHierarquia": "Soberania / Defesa do Estado / Segurança Pública"},
        ],
        "1": [],  # sem classificação: registrada para não ser buscada de novo
    }
    registros = temas.normalizar(payload)
    assert [(r["proposicao_id_externo"], r["tema"]) for r in registros] == [
        ("1", SEM_CLASSIFICACAO),
        ("157013", "Defesa do Estado"),
        ("157013", "Educação"),
    ]


def test_orientacoes_do_senado_ligadas_pelo_sequencial():
    votacao = {
        "codigoSessaoVotacao": 7104, "sequencialVotacao": 4415, "dataSessao": "2026-08-12",
        "descricaoVotacao": "PL", "identificacao": "PL 1/2026", "votacaoSecreta": "N",
        "informeLegislativo": {"siglaColegiado": "PLEN"},
        "votos": [{"codigoParlamentar": 1, "siglaVotoParlamentar": "Sim"}],
    }  # fmt: skip
    payload = {
        "votacoes": [votacao],
        "orientacoes": {
            "2026-08-12": {
                "votacoes": [
                    {
                        "sequencialVotacao": 4415,
                        "orientacoesLideranca": [
                            {"partido": "Governo", "voto": "SIM"},
                            {"partido": "MDB", "voto": "NÃO"},  # partido: não guardamos
                            {"partido": "Oposição", "voto": "LIVRE"},
                        ],
                    },
                    {
                        "sequencialVotacao": 9999,
                        "orientacoesLideranca": [{"partido": "Governo", "voto": "NÃO"}],
                    },
                ]
            }
        },
    }
    _, _, orientacoes = senado.normalizar(payload)
    assert orientacoes == [
        {"id_externo_votacao": "7104", "bancada": "Governo", "orientacao": "Sim"},
        {"id_externo_votacao": "7104", "bancada": "Oposição", "orientacao": "Liberado"},
    ]


def test_espera_respeita_retry_after():
    com_header = httpx.Response(429, headers={"Retry-After": "7"})
    assert comum._espera(com_header, 1) == 7
    assert comum._espera(httpx.Response(429), 2) == 4
    assert comum._espera(None, 3) == 8
