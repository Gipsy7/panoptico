"""Página de um projeto: GET /projetos/{casa}/{id_externo}, mapa de etapas e discursos."""

from datetime import date, datetime

import pytest

from app.models import Autoria, Discurso, PautaItem, ProposicaoTema, Tramitacao
from app.services.projeto_detalhe import escolher_principal
from app.services.projeto_etapas import etapa_do_passo
from tests.helpers_projetos import ingestao, parlamentar, proposicao, votacao

# (tipo, texto oficial, etapa esperada): textos reais de tramitação (FONTES_DE_DADOS.md).
TEXTOS_REAIS = [
    ("Apresentação de Proposição", "Apresentação do Projeto de Lei n. 2338/2023", "Apresentado"),
    ("Designação de Relator(a)", "Designado Relator, Dep. Fulano (PXX-SC)", "Relator escolhido"),
    ("Recebimento - Relator(a)", "Recebimento pelo relator", "Relator escolhido"),
    ("Parecer do(a) Relator(a)", "Parecer do Relator, Dep. Fulano (PXX-SC), pela aprovação",
     "Parecer na comissão"),
    ("Distribuição", "Distribuído à Comissão de Educação (CE)", "Nas comissões"),
    ("Aprovação de Urgência (154, 155 ou 64 CF)", "Aprovado o Requerimento de urgência",
     "Outro andamento"),
    ("Votação (Plenário)", "Votação em turno único", "Votado no Plenário"),
    ("Aprovação de Proposição (Plenário)", "Aprovado o projeto", "Votado no Plenário"),
    ("Rejeição de Proposição (Plenário)", "Rejeitado o projeto", "Votado no Plenário"),
    ("Tramitação", "Remessa ao Senado Federal por meio do Of. nº 41/2026", "Enviado à outra Casa"),
    ("Apresentação de Proposição", "Remessa do Ofício informando restituição de autógrafo "
     "sancionado", "Virou lei"),
    ("Transformação em Norma Jurídica", "Transformado em Lei Complementar nº 214", "Virou lei"),
    (None, "SANCIONADA. LEI COMPLEMENTAR nº 214, de 2025.", "Virou lei"),
    (None, "Distribuído à Senadora Leila Barros, para emitir relatório.", "Relator escolhido"),
    (None, "Incluída em Ordem do Dia da sessão deliberativa ordinária.", "Na pauta do Plenário"),
    (None, "A matéria vai ao arquivo.", "Arquivado"),
    (None, "Remessa à sanção.", "Enviado à sanção"),
    (None, "Remetido Ofício SF nº 289 encaminhando autógrafo do projeto para revisão.",
     "Enviado à outra Casa"),
    (None, "Vetado totalmente pelo Presidente da República. Mensagem de veto nº 12.", "Vetado"),
    (None, "Recebido o relatório do Senador Fulano, com parecer favorável.", "Parecer na comissão"),
    ("Arquivamento", "Arquivado nos termos do art. 105 do RICD", "Arquivado"),
    (None, "Texto sem nenhuma pista conhecida.", "Outro andamento"),
]  # fmt: skip


@pytest.mark.parametrize(("tipo", "texto", "etapa"), TEXTOS_REAIS)
def test_mapa_de_etapas(tipo, texto, etapa):
    assert etapa_do_passo(tipo, texto) == etapa


def test_etapa_pela_situacao_quando_o_texto_nao_diz():
    assert etapa_do_passo(None, "Texto neutro.", "REMETIDA À SANÇÃO") == "Enviado à sanção"
    assert etapa_do_passo(None, "Texto neutro.", None) == "Outro andamento"
    assert etapa_do_passo(None, "Desarquivada a proposição.") != "Arquivado"


def _cenario(session):
    """PL 2338/2023 com 3 votações, 5 pessoas, discursos e tramitação."""
    ana, bia, caio, dora, edu = (
        parlamentar(session, nome, uf, partido)
        for nome, uf, partido in [
            ("Ana", "SC", "PXX"),
            ("Bia", "SC", "PYY"),
            ("Caio", "SP", "PXX"),
            ("Dora", "SP", "PXX"),
            ("Edu", "AC", "PZZ"),
        ]
    )
    p = proposicao(
        session, "100", "PL", 2338, 2023, "Marco legal da inteligência artificial.",
        autor_descricao=None, situacao="Aguardando Apreciação pelo Senado Federal",
        relator="Dep. Fulano", relator_parlamentar_id=ana.id, origem="legislatura",
    )  # fmt: skip
    session.add(Autoria(proposicao_id=p.id, parlamentar_id=bia.id, primeiro_autor=True))
    session.add_all(
        [
            ProposicaoTema(casa="camara", proposicao_id_externo="100", tema="Ciência"),
            ProposicaoTema(casa="camara", proposicao_id_externo="100", tema="Sem classificação"),
        ]
    )
    # Dia 1: requerimento (nominal) e depois o texto-base. Dia 2: destaque.
    votacao(session, "1-1", "100", date(2026, 9, 2), {ana.id: "Sim"},
            descricao="Aprovado o Requerimento de urgência.", resultado="aprovada")  # fmt: skip
    base = votacao(
        session, "2-1", "100", date(2026, 9, 3),
        {ana.id: "Sim", bia.id: "Não", caio.id: "Sim", dora.id: "Abstenção", edu.id: "Sim"},
        descricao="Aprovado o texto-base.", resultado="aprovada",
        placar_sim=346, placar_nao=96,
    )  # fmt: skip
    votacao(session, "2-2", "100", date(2026, 9, 3), {ana.id: "Sim", bia.id: "Não"},
            descricao="Rejeitado o Destaque da bancada X.", resultado="rejeitada")  # fmt: skip
    ing = ingestao(session, "camara_discursos", date(2026, 10, 18))
    for i, (pid, hora, sumario) in enumerate(
        [
            (bia.id, 14, "Criticou o texto."),
            (ana.id, 13, "Defendeu o texto."),
            (dora.id, 15, "Orientou a bancada."),
        ]
    ):
        session.add(
            Discurso(casa="camara", id_externo=f"d{i}", parlamentar_id=pid, data=date(2026, 9, 3),
                     data_hora=datetime(2026, 9, 3, hora), fase="Ordem do Dia",
                     tipo="DISCUSSÃO", sumario=sumario, url_texto="https://t", url_video=None,
                     proposicao_id_externo="100", ingestao_id=ing.id)
        )  # fmt: skip
    # Quem falou e não votou (Caio registrou voto, então use outra pessoa sem voto).
    sem_voto = parlamentar(session, "Fabi", "RS", "PYY")
    session.add(
        Discurso(casa="camara", id_externo="d9", parlamentar_id=sem_voto.id, data=date(2026, 9, 3),
                 data_hora=datetime(2026, 9, 3, 12), fase="Ordem do Dia", tipo="PELA ORDEM",
                 sumario="Falou.", proposicao_id_externo="100", ingestao_id=ing.id)
    )  # fmt: skip
    # Discurso do mesmo dia que a ingestão não ligou a nenhum projeto: só contado.
    session.add(
        Discurso(casa="camara", id_externo="d10", parlamentar_id=ana.id, data=date(2026, 9, 3),
                 data_hora=datetime(2026, 9, 3, 16), fase="Ordem do Dia", tipo="DISCUSSÃO",
                 sumario="Cita 5 projetos.", proposicao_id_externo=None, ingestao_id=ing.id)
    )  # fmt: skip
    ing_t = ingestao(session, "camara_tramitacoes")
    for ordem, (dia, orgao, tipo, texto) in enumerate(
        [
            (date(2023, 5, 1), "PLEN", "Apresentação de Proposição", "Apresentação do PL"),
            (date(2023, 6, 1), "CCJC", "Designação de Relator(a)", "Designado Relator"),
            (date(2026, 9, 3), "PLEN", "Aprovação de Proposição (Plenário)", "Aprovado"),
            (date(2026, 9, 4), "PLEN", "Tramitação", "Remessa ao Senado Federal"),
        ],
        start=1,
    ):
        session.add(
            Tramitacao(casa="camara", proposicao_id_externo="100", ordem=ordem,
                       data=datetime(dia.year, dia.month, dia.day, 10), orgao=orgao, tipo=tipo,
                       descricao=texto, ingestao_id=ing_t.id)
        )  # fmt: skip
    session.add(
        PautaItem(casa="camara", data=date(2099, 1, 5), sessao="e1", proposicao_id_externo="100",
                  url="https://pauta", ingestao_id=ing_t.id)
    )  # fmt: skip
    ingestao(session, "camara_proposicoes", date(2026, 10, 19))
    session.flush()
    return {"ana": ana, "bia": bia, "caio": caio, "dora": dora, "edu": edu, "base": base}


def test_ficha_votacoes_e_pauta(client, session):
    c = _cenario(session)
    resposta = client.get("/projetos/camara/100")
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["rotulo"] == "PL 2338/2023"
    assert (corpo["sigla"], corpo["numero"], corpo["ano"]) == ("PL", 2338, 2023)

    ficha = corpo["ficha"]
    assert ficha["temas"] == ["Ciência"]  # sem "Sem classificação"
    assert [a["nome"] for a in ficha["autores"]] == ["Bia"]
    assert ficha["autores"][0]["parlamentar_id"] == c["bia"].id
    assert ficha["relator"] == "Dep. Fulano"
    assert ficha["relator_parlamentar_id"] == c["ana"].id
    assert ficha["situacao"].startswith("Aguardando Apreciação")
    assert ficha["url_oficial"] == "https://exemplo/100"
    assert ficha["fonte_nome"] and ficha["atualizado_em"].startswith("2026-10-19")

    v = corpo["votacoes"]
    assert [i["id_externo"] for i in v["itens"]] == ["2-2", "2-1", "1-1"]  # mais recente 1º
    base = next(i for i in v["itens"] if i["id_externo"] == "2-1")
    assert base["link"] == "/votacao/camara/2-1"
    assert base["placar_publicado"] == {"sim": 346, "nao": 96, "abstencao": None}
    assert base["placar_contado"] == {
        "sim": 3,
        "nao": 1,
        "abstencao": 1,
        "obstrucao": 0,
        "outros": 0,
    }
    assert v["aviso"] is None
    assert v["atualizado_em"] is None  # sem carga de votações neste teste

    assert corpo["pauta"]["proxima"] == {
        "data": "2099-01-05",
        "sessao": "e1",
        "url": "https://pauta",
    }


def test_votacao_principal_ignora_requerimento_e_destaque(client, session):
    _cenario(session)
    corpo = client.get("/projetos/camara/100").json()
    principal = corpo["votacao_principal"]
    assert principal["votacao"]["id_externo"] == "2-1"  # a última de 3 que não é destaque
    assert "requerimento" in principal["regra"]
    grupos = {g["chave"]: g for g in principal["grupos"]}
    assert [g["chave"] for g in principal["grupos"]] == ["sim", "nao", "outros"]
    assert [p["nome"] for p in grupos["sim"]["pessoas"]] == ["Ana", "Caio", "Edu"]
    assert [p["nome"] for p in grupos["nao"]["pessoas"]] == ["Bia"]
    assert [(p["nome"], p["registro"]) for p in grupos["outros"]["pessoas"]] == [
        ("Dora", "Abstenção")
    ]
    assert grupos["sim"]["quantidade"] == 3
    # Partidos do maior para o menor: PXX tem Ana e Caio; PZZ, Edu.
    assert grupos["sim"]["partidos"] == [
        {"partido": "PXX", "quantidade": 2},
        {"partido": "PZZ", "quantidade": 1},
    ]
    assert set(grupos["sim"]["pessoas"][0]) == {
        "parlamentar_id",
        "nome",
        "partido",
        "uf",
        "registro",
    }
    # Placar por estado: SP (Caio sim, Dora outros) e SC (Ana sim, Bia não) empatam em 2; AC 1.
    assert principal["por_uf"] == [
        {"uf": "SC", "sim": 1, "nao": 1, "outros": 0, "total": 2},
        {"uf": "SP", "sim": 1, "nao": 0, "outros": 1, "total": 2},
        {"uf": "AC", "sim": 1, "nao": 0, "outros": 0, "total": 1},
    ]


def test_escolher_principal_cai_na_ultima_quando_todas_sao_acessorias(session):
    parlamentar(session, "X", "SC", "PXX")
    a = votacao(session, "1-1", "5", date(2026, 1, 1), descricao="Aprovado o requerimento.")
    b = votacao(session, "1-2", "5", date(2026, 1, 2), descricao="Rejeitada a emenda nº 3.")
    assert escolher_principal([a, b]) is b
    assert escolher_principal([]) is None
    c = votacao(session, "1-3", "5", date(2026, 1, 3), descricao="Rejeitado o Recurso nº 2.")
    assert escolher_principal([a, b, c]) is c  # recurso também é acessório
    d = votacao(session, "1-0", "5", date(2025, 12, 1), descricao="Aprovado o texto.")
    assert escolher_principal([d, a, b, c]) is d


def test_discursos_agrupados_pelo_voto_do_orador(client, session):
    _cenario(session)
    dias = client.get("/projetos/camara/100").json()["discursos"]["dias"]
    assert len(dias) == 1
    dia = dias[0]
    assert dia["data"] == "2026-09-03"
    assert dia["votacao_id_externo"] == "2-2"  # a última votação nominal do dia
    assert dia["total"] == 4
    grupos = {g["chave"]: g for g in dia["grupos"]}
    assert [g["rotulo"] for g in dia["grupos"]] == [
        "votou Sim",
        "votou Não",
        "outro registro",
        "falou e não registrou voto",
    ]
    # Na última votação do dia (destaque) Ana votou Sim, Bia Não; Dora não tem registro nela.
    assert [d["nome"] for d in grupos["sim"]["discursos"]] == ["Ana"]
    assert [d["nome"] for d in grupos["nao"]["discursos"]] == ["Bia"]
    assert grupos["outro"]["discursos"] == []
    # Ordem cronológica dentro do grupo: Fabi falou às 12h, Dora às 15h.
    assert [d["nome"] for d in grupos["sem_voto"]["discursos"]] == ["Fabi", "Dora"]
    discurso = grupos["sim"]["discursos"][0]
    assert discurso["sumario"] == "Defendeu o texto."
    assert discurso["url_texto"] == "https://t"
    assert discurso["url_video"] is None
    assert discurso["fase"] == "Ordem do Dia"
    assert "Ana" in discurso["nome"] and discurso["partido"] == "PXX" and discurso["uf"] == "SC"

    corpo = client.get("/projetos/camara/100").json()
    assert corpo["discursos"]["fonte_nome"]
    assert "sem juízo" in corpo["discursos"]["aviso"]
    # Discurso do dia sem projeto atribuído: contador, lista vazia.
    do_dia = corpo["discursos_do_dia"]
    assert do_dia["quantidade_nao_atribuida"] == 1
    assert do_dia["itens"] == []
    assert do_dia["atualizado_em"].startswith("2026-10-18")


def test_caminho_com_etapas(client, session):
    _cenario(session)
    caminho = client.get("/projetos/camara/100").json()["caminho"]
    assert [p["etapa"] for p in caminho["itens"]] == [
        "Apresentado",
        "Relator escolhido",
        "Votado no Plenário",
        "Enviado à outra Casa",
    ]
    assert caminho["itens"][1]["orgao"] == "CCJC"
    assert caminho["itens"][3]["descricao"] == "Remessa ao Senado Federal"
    assert caminho["atualizado_em"] is not None


def test_projeto_sem_votacao_nominal(client, session):
    proposicao(session, "200", "PL", 9, 2025, "Sem votação.", autor_descricao="Poder Executivo")
    corpo = client.get("/projetos/camara/200").json()
    assert corpo["votacoes"]["itens"] == []
    assert "votação nominal" in corpo["votacoes"]["aviso"]
    assert "simbólica" in corpo["votacoes"]["aviso"]
    assert corpo["votacao_principal"] is None
    assert corpo["discursos"]["dias"] == []
    assert corpo["discursos_do_dia"]["quantidade_nao_atribuida"] == 0
    assert corpo["caminho"]["itens"] == []
    assert corpo["pauta"]["proxima"] is None
    assert corpo["ficha"]["autor_descricao"] == "Poder Executivo"
    assert corpo["ficha"]["autores"] == []


def test_projeto_so_existe_na_votacao(client, session):
    ana = parlamentar(session, "Ana", "SC", "PXX")
    votacao(session, "7-1", "321", date(2026, 5, 5), {ana.id: "Sim"}, rotulo="PL 759/2015",
            ementa="Ementa antiga.", resultado="aprovada")  # fmt: skip
    corpo = client.get("/projetos/camara/321").json()
    assert corpo["rotulo"] == "PL 759/2015"
    assert (corpo["sigla"], corpo["numero"], corpo["ano"]) == ("PL", 759, 2015)
    assert corpo["ementa"] == "Ementa antiga."
    assert corpo["ficha"]["origem"] is None
    assert corpo["ficha"]["virou_lei"] is None
    assert corpo["ficha"]["url_oficial"].endswith("idProposicao=321")
    assert corpo["votacao_principal"]["votacao"]["id_externo"] == "7-1"


def test_projeto_inexistente_e_casa_invalida(client, session):
    assert client.get("/projetos/camara/nao-existe").status_code == 404
    assert client.get("/projetos/stf/1").status_code == 422
    assert client.get("/projetos/local/999999").status_code == 404
