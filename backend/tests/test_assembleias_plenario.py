"""Presença, votos e projetos de assembleias acrescentados em 29/10/2026: ALRN (presença e votos
pela API da Transparência Legislativa), ALESE e ALEGO (projetos e presença pela API do PLE) e
ALECE (votações nominais em PDF). Amostras recortadas das respostas reais."""

import io
import json
import zipfile
from datetime import date

import httpx
import respx

from ingestion.assembleias import alece_votos, alego, alese, alrn, ple

# ---------------- ALRN ----------------
RN_SESSOES = [
    {"id": 3048, "dataInicio": "2026-10-28T10:30:00.000Z", "tipoReuniao": {"id": 1}},
    {"id": 2843, "dataInicio": "2025-11-04T10:30:00.000Z", "tipoReuniao": {"id": 1}},
]
RN_CHAMADA_3048 = {
    "dados": [
        {
            "id": 8,
            "nomeParlamentar": "DEPUTADA CRISTIANE DANTAS",
            "evento": {"id": 8, "chave": "presenca"},
        },
        {"id": 56, "nomeParlamentar": "DEPUTADA DIVANEIDE BASÍLIO", "evento": None},
        {
            "id": 7,
            "nomeParlamentar": "DEPUTADO CORONEL AZEVEDO",
            "evento": {"id": 9, "chave": "ausencia-justificada"},
        },
    ]
}
RN_CHAMADA_2843 = {
    "dados": [
        {
            "id": 8,
            "nomeParlamentar": "DEPUTADA CRISTIANE DANTAS",
            "evento": {"id": 8, "chave": "presenca"},
        },
        {
            "id": 56,
            "nomeParlamentar": "DEPUTADA DIVANEIDE BASÍLIO",
            "evento": {"id": 3, "chave": "licenca"},
        },
    ]
}
RN_VOTADAS = [
    {
        "id": 56082,
        "ementa": "Veto total ao Projeto de Lei nº 12/2025.",
        "propositura": {"tipo": {"sigla": "VET"}, "numero": 7, "ano": 2025},
        "reuniaoProcesso": [{"resultadoVotacao": "R", "reuniao": {"id": 2843}}],
    },
    {
        "id": 63996,
        "ementa": "Requer informações.",
        "propositura": {"tipo": {"sigla": "REQ"}, "numero": 2147, "ano": 2026},
        "reuniaoProcesso": [{"resultadoVotacao": "A", "reuniao": {"id": 3048}}],
    },
    {  # votada numa reunião de comissão: não é Plenário
        "id": 63791,
        "propositura": {"tipo": {"sigla": "PL"}, "numero": 394, "ano": 2026},
        "reuniaoProcesso": [{"resultadoVotacao": "A", "reuniao": {"id": 3029}}],
    },
]
RN_EXTRATO_ABERTO = {
    "tipoVotacao": "A",
    "votacao": {
        "dados": [
            {"voto": 0, "parlamentar": {"id": 8, "nomeParlamentar": "DEPUTADA CRISTIANE DANTAS"}},
            {"voto": 2, "parlamentar": {"id": 56, "nomeParlamentar": "DEPUTADA DIVANEIDE BASÍLIO"}},
            {"voto": 1, "parlamentar": {"id": 99, "nomeParlamentar": "DEPUTADO QUE JA SAIU"}},
        ],
        "resumo": {"sim": 1, "nao": 1, "abstencao": 1},
    },
}
RN_EXTRATO_OSTENSIVO = {"tipoVotacao": "O", "votacao": {"dados": [], "resumo": {}}}


def _bruto_rn() -> dict[str, bytes]:
    return {
        "sessoes.json": json.dumps(RN_SESSOES).encode(),
        "presenca/3048.json": json.dumps(RN_CHAMADA_3048).encode(),
        "presenca/2843.json": json.dumps(RN_CHAMADA_2843).encode(),
        "votadas.json": json.dumps(RN_VOTADAS).encode(),
        "votacao/56082-2843.json": json.dumps(RN_EXTRATO_ABERTO).encode(),
        "votacao/63996-3048.json": json.dumps(RN_EXTRATO_OSTENSIVO).encode(),
    }


def test_alrn_votacoes_so_do_plenario():
    assert alrn.votacoes_em_plenario(RN_VOTADAS, {3048, 2843}) == [(56082, 2843), (63996, 3048)]


def test_alrn_presenca_conta_ausencia_e_ignora_licenca():
    ids = {"CRISTIANE DANTAS": "114", "DIVANEIDE BASILIO": "138", "CORONEL AZEVEDO": "126"}
    frequencia, _, _ = alrn.plenario(_bruto_rn(), ids)
    assert frequencia["CRISTIANE DANTAS"] == (2, 2)
    assert frequencia["DIVANEIDE BASILIO"] == (1, 0)  # ausente numa, de licença na outra
    assert frequencia["CORONEL AZEVEDO"] == (1, 0)  # ausência justificada conta como sessão


def test_alrn_so_voto_aberto_com_lista_vira_votacao_nominal():
    ids = {"CRISTIANE DANTAS": "114", "DIVANEIDE BASILIO": "138"}
    _, votacoes, votos = alrn.plenario(_bruto_rn(), ids)
    assert votacoes == [
        {
            "id_externo": "56082-2843",
            "materia": "VET 7/2025: Veto total ao Projeto de Lei nº 12/2025.",
            "materia_id_externo": "VET-7-2025",
            "resultado": "Rejeitado",
            "data": "2025-11-04",
            "url": "https://transparencialegislativa.al.rn.leg.br/projeto/56082",
            "sim": 1,  # quem já saiu da Casa conta no total, mas não ganha voto ligado
            "nao": 1,
            "abstencoes": 1,
        }
    ]
    assert votos == [
        {"votacao": "56082-2843", "parlamentar": "114", "voto": "Não"},
        {"votacao": "56082-2843", "parlamentar": "138", "voto": "Abstenção"},
    ]


def test_alrn_plenario_de_raw_le_o_zip(tmp_path):
    caminho = tmp_path / "plenario.zip"
    caminho.write_bytes(alrn.empacotar(_bruto_rn()))
    assert alrn.plenario_bruto(None, 2025, caminho) == _bruto_rn()


@respx.mock
def test_alrn_baixar_plenario_pede_extrato_so_do_plenario(monkeypatch):
    monkeypatch.setattr(alrn, "PAUSA", 0)
    respx.get(alrn.API + "reuniao").mock(
        side_effect=lambda r: httpx.Response(
            200, json={"dados": RN_SESSOES if r.url.params["tipoReuniao"] == "1" else []}
        )
    )
    respx.get(alrn.API + "reuniao/presenca/3048").mock(
        return_value=httpx.Response(200, json=RN_CHAMADA_3048)
    )
    respx.get(alrn.API + "reuniao/presenca/2843").mock(
        return_value=httpx.Response(200, json=RN_CHAMADA_2843)
    )
    respx.get(alrn.API + "processo/ultimas-votacoes").mock(
        return_value=httpx.Response(200, json={"dados": RN_VOTADAS})
    )
    extrato = respx.get(url__regex=r".*/detalhamento-votacao/.*").mock(
        return_value=httpx.Response(200, json=RN_EXTRATO_OSTENSIVO)
    )
    with httpx.Client() as client:
        arquivos = alrn.baixar_plenario(client, 2025)
    assert extrato.call_count == 2  # a votação da comissão (3029) não é pedida
    assert sorted(k for k in arquivos if k.startswith("votacao/")) == [
        "votacao/56082-2843.json",
        "votacao/63996-3048.json",
    ]


# ---------------- PLE (ALESE e ALEGO) ----------------
def _so(sigla: str, item: dict):
    """Resposta da API de proposições: o item só na sigla e no ano dele."""

    def responder(r):
        bate = r.url.params.get("sigla") == sigla and r.url.params["ano"] == item["ano"]
        return httpx.Response(
            200, json={"Data": [item] if bate else [], "Paginacao": {"quantidade": "1"}}
        )

    return responder


def _parlamentar(id_, autor, nome, civil, frequencia):
    return {
        "parlamentarID": id_,
        "autorID": autor,
        "parlamentarNome": nome,
        "parlamentarRazaoSocial": civil,
        "parlamentarSituacao": "Ativo",
        "parlamentarLegislatura": "20",
        "frequenciaPlenario": frequencia,
    }


GO_FREQUENCIA = [
    {
        "frequenciaSituacaoNome": "Presente",
        "frequenciaSituacaoAnos": [
            {"ano": 2025, "quantidade": "90"},
            {"ano": 2026, "quantidade": "67"},
        ],
    },
    {
        "frequenciaSituacaoNome": "Falta Justificada",
        "frequenciaSituacaoAnos": [
            {"ano": 2025, "quantidade": "16"},
            {"ano": 2026, "quantidade": "10"},
        ],
    },
    {
        "frequenciaSituacaoNome": "Falta não Justificada",
        "frequenciaSituacaoAnos": [
            {"ano": 2025, "quantidade": "15"},
            {"ano": 2026, "quantidade": "8"},
        ],
    },
    {
        "frequenciaSituacaoNome": "Licenciado",
        "frequenciaSituacaoAnos": [
            {"ano": 2025, "quantidade": "3"},
            {"ano": 2026, "quantidade": "0"},
        ],
    },
]


def test_ple_frequencia_conta_falta_nao_justificada():
    deputado = {"frequenciaPlenario": GO_FREQUENCIA}
    assert ple.frequencia(deputado, {2025, 2026}) == (90 + 67 + 16 + 10 + 15 + 8, 157)


def test_ple_endereco_do_pdf_sem_dominio_repetido():
    repetido = "https://aleselegis.al.se.leg.br/https://aleselegis.al.se.leg.br/Arquivo/x.pdf"
    assert ple._arquivo(repetido) == "https://aleselegis.al.se.leg.br/Arquivo/x.pdf"
    assert ple._arquivo("https://www3.al.es.gov.br/a.pdf") == "https://www3.al.es.gov.br/a.pdf"
    assert ple._arquivo(None) is None


def test_alego_liga_api_ao_portal_por_nome_exato_e_tse():
    parlamentares = [
        _parlamentar(87, "32665", "Alessandro Moreira", "ALESSANDRO MOREIRA DOS SANTOS", []),
        _parlamentar(59, "30878", "Del. Eduardo Prado", "EDUARDO JOSÉ DO PRADO", []),
        _parlamentar(60, "30879", "Sem Par", "FULANO DE TAL", []),
    ]
    lista = [
        {"id": "808", "nome": "Alessandro Moreira"},
        {"id": "143", "nome": "Delegado Eduardo Prado"},
    ]
    tse = [("DELEGADO EDUARDO PRADO", "EDUARDO JOSÉ DO PRADO")]
    ligados = alego.ligar_api(parlamentares, lista, tse)
    assert {k: v["parlamentarID"] for k, v in ligados.items()} == {"808": 87, "143": 59}
    assert alego.ligar_api(parlamentares, lista, []).keys() == {"808"}  # sem TSE, só o exato


@respx.mock
def test_alego_coleta_projetos_e_presenca_da_api(monkeypatch):
    monkeypatch.setattr(alego, "PAUSA", 0)
    respx.get(alego.LISTA).mock(
        return_value=httpx.Response(
            200,
            text='<tr data-filter-key=\'x\'><td data-title="Nome"> <a class="link" '
            "href=/deputados/perfil/808>Alessandro Moreira</a> </td></tr>",
        )
    )
    respx.get(alego.API + "verbas_indenizatorias/periodos").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(alego.PLE + "parlamentar/").mock(
        return_value=httpx.Response(
            200,
            json={
                "parlamentares": [
                    _parlamentar(
                        87,
                        "32665",
                        "Alessandro Moreira",
                        "ALESSANDRO MOREIRA DOS SANTOS",
                        GO_FREQUENCIA,
                    )
                ]
            },
        )
    )
    pl = {
        "processo": "22674",
        "ano": "2026",
        "sigla": "PLO",
        "numero": "934",
        "assunto": "INSTITUI O PROGRAMA ESTADUAL.",
        "data": "28/10/2026 16:20:52",
        "situacao": "Tramitando",
        "arquivo": "https://alegodigital.al.go.leg.br/https://alegodigital.al.go.leg.br/Arquivo/a.pdf",
        "AutorRequerenteDados": {
            "autorId": 32665,
            "nomeRazao": "ALESSANDRO MOREIRA DOS SANTOS",
            "cpf_cnpj": "00000000000",
        },
    }
    respx.get(alego.PLE + "proposicao/").mock(side_effect=_so("PLO", pl))
    casa = alego.coletar(date(2026, 10, 29))
    d = casa["vereadores"][0]
    assert (d["sessoes"], d["presencas"]) == (206, 157)
    assert d["proposicoes_por_tipo"] == {"Projeto de Lei": 1}
    assert d["projetos"][0]["url"] == "https://alegodigital.al.go.leg.br/Arquivo/a.pdf"
    assert "00000000000" not in json.dumps(casa, default=str)  # o CPF do autor não é guardado


SE_CARTAO = """
<a href="https://aleselegis.al.se.leg.br/spl/parlamentar.aspx?id=426" target="_blank">
<img loading="lazy" src="https://al.se.leg.br/wp-content/uploads/2023/06/Luiz-Garibalde.jpg" />
</a>
<h5 class="qodef-item-title">
<a href="https://aleselegis.al.se.leg.br/spl/parlamentar.aspx?id=426" target="_blank">
Garibalde Mendon&ccedil;a			</a>
</h5>
<div class="qodef-ptf-category-holder"><span>MDB</span></div>
"""


@respx.mock
def test_alese_coleta_projetos_pela_api(monkeypatch):
    monkeypatch.setattr(alese, "PAUSA", 0)
    respx.get(alese.SITE).mock(return_value=httpx.Response(200, text=SE_CARTAO))
    respx.get(alese.SPL + "parlamentar.aspx").mock(return_value=httpx.Response(200, text=""))
    respx.get(alese.API + "parlamentar/").mock(
        return_value=httpx.Response(
            200,
            json={
                "parlamentares": [
                    _parlamentar(426, "386", "Garibalde Mendonça", "Garibalde Mendonça", [])
                ]
            },
        )
    )
    pl = {
        "processo": "5803",
        "ano": "2026",
        "sigla": "PL",
        "numero": "300",
        "assunto": "Dispõe sobre x.",
        "data": "29/10/2026 12:09:33",
        "situacao": "Tramitando",
        "arquivo": None,
        "AutorRequerenteDados": {"autorId": 386, "nomeRazao": "Garibalde Mendonça"},
    }
    respx.get(alese.API + "proposicao/").mock(side_effect=_so("PL", pl))
    casa = alese.coletar(date(2026, 10, 29))
    d = casa["vereadores"][0]
    assert d["id_externo"] == "426"
    assert d["proposicoes_por_tipo"] == {"Projeto de Lei": 1}
    assert d["projetos"][0]["id_externo"] == "PL-300-2026"


# ---------------- ALECE ----------------
CE_CSV = (
    "LEGISLATURA;SESSÃO;MATERIA;URL\n"
    "31.ª LEGISLATURA;59.ª SESSÃO ORDINÁRIA;74/2026 - Projeto de Lei - Autoriza operação de "
    "crédito.;/uploads/votacao_nominal_materia/abc123.pdf\n"
    "31.ª LEGISLATURA;12.ª SESSÃO ORDINÁRIA;10/2023 - Projeto de Lei - Antigo.;"
    "/uploads/votacao_nominal_materia/velho.pdf\n"
).encode()
CE_TEXTO = """SIM NÃO ABSTENÇÃO BRANCO
1 Evandro Leitão PT - Partido dos Trabalhadores
4 Danniel Oliveira MDB - Movimento Democrático Brasileiro SIM (P)
7 David Durand REPLUBLICANOS SIM (V)
8 Emilia Pessoa PSDB - Partido da Social Democracia Brasileira NÃO (V)
15 Antonio Henrque PDT - Partido Democrático Trabalhista NÃO (P)
MATÉRIA - PL nº 74/2026 - Projeto de Lei
Presidente da Sessão: Osmar Baquit       Data: 10 /07/2026   Horário: 12:22
Processo de votação:          NOMINAL           Resultado: APROVADO
7 David Durand REPLUBLICANOS SIM (V)
3
2 2 0 0
"""


def test_alece_relatorio_le_votos_total_e_data():
    rel = alece_votos.relatorio(CE_TEXTO)
    assert rel["data"] == "2026-07-10"
    assert rel["resultado"] == "Aprovado"
    assert rel["total"] == (2, 2, 0, 0)
    assert rel["linhas"][7] == ("David Durand REPLUBLICANOS", "Sim")  # repetida na outra página
    assert rel["linhas"][1] == ("Evandro Leitão PT - Partido dos Trabalhadores", None)
    assert alece_votos.relatorio("Processo de votação: SIMBÓLICA") is None


def test_alece_voto_liga_so_pelo_comeco_unico_do_nome():
    nomes = {
        "DAVID DURAND": "david-durand",
        "EMILIA PESSOA": "emilia-pessoa",
        "DAVI": "davi",
        "ANTONIO HENRIQUE": "antonio-henrique",
    }
    assert alece_votos.dono("David Durand REPLUBLICANOS", nomes) == "david-durand"
    assert alece_votos.dono("Antonio Henrque PDT", nomes) is None  # grafia diferente: sem dono
    linhas = alece_votos.materias(CE_CSV)
    assert [x["URL"].rsplit("/", 1)[-1] for x in alece_votos.recentes(linhas, 2025)] == [
        "abc123.pdf"
    ]
    rel = alece_votos.relatorio(CE_TEXTO)
    votacoes, votos = alece_votos.votacoes([(linhas[0], rel)], nomes, 2025)
    assert votacoes[0]["sim"] == 2 and votacoes[0]["nao"] == 2
    assert votacoes[0]["url"] == (
        "https://transparencia.al.ce.gov.br/uploads/votacao_nominal_materia/abc123.pdf"
    )
    assert votos == [
        {"votacao": "abc123", "parlamentar": "david-durand", "voto": "Sim"},
        {"votacao": "abc123", "parlamentar": "emilia-pessoa", "voto": "Não"},
    ]
    assert alece_votos.votacoes([(linhas[0], rel)], nomes, 2027) == ([], [])


def test_alece_votos_de_raw(tmp_path, monkeypatch):
    from ingestion.assembleias import alece

    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("lista.csv", CE_CSV)
    caminho = tmp_path / "votos.zip"
    caminho.write_bytes(memoria.getvalue())
    assert alece.votos_brutos(None, 2025, caminho) == {"lista.csv": CE_CSV}
