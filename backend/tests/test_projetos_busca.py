"""Busca de projetos e votações: GET /projetos."""

from datetime import date, datetime
from pathlib import Path

import pytest

from app.models import CanalOficial, Discurso, PautaItem, ProposicaoTema, Tramitacao
from app.services import projetos_busca, texto_busca
from tests.helpers_projetos import (
    ingestao,
    mandato_local,
    municipio,
    parlamentar,
    projeto_local,
    proposicao,
    votacao,
    votacao_local,
)

HOJE = date(2026, 10, 21)


def _busca(client, **params) -> dict:
    resposta = client.get("/projetos", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _rotulos(corpo: dict) -> list[str]:
    return [i["rotulo"] for i in corpo["itens"]]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("PL 2338/2023", ("PL", 2338, 2023)),
        ("pl 2338", ("PL", 2338, None)),
        ("PL nº 2.338, de 2023", ("PL", 2338, 2023)),
        ("PL n° 2338 de 2023", ("PL", 2338, 2023)),
        ("2338/2023", (None, 2338, 2023)),
        ("2338", (None, 2338, None)),
        ("PEC 3/2021", ("PEC", 3, 2021)),
        ("MP 1343", ("MPV", 1343, None)),
        ("MP 1343/2026", ("MPV", 1343, 2026)),
    ],
)
def test_reconhece_o_numero_em_varios_formatos(texto, esperado):
    achou = projetos_busca.reconhecer_numero(texto)
    assert (achou["sigla"], achou["numero"], achou["ano"]) == esperado


@pytest.mark.parametrize("texto", ["saude mental", "rua 12", "reforma tributaria 2023", "xyz 12"])
def test_palavras_nao_sao_numero(texto):
    assert projetos_busca.reconhecer_numero(texto) is None


def test_expressao_do_indice_e_a_da_consulta():
    """A migração e a consulta usam o mesmo texto de expressão (senão o índice não é usado)."""
    migracao = Path(__file__).parents[1] / "alembic/versions/0055_proposicao_ampliada.py"
    texto = migracao.read_text(encoding="utf-8")
    modelo = ("to_tsvector('portuguese', translate(lower({coluna}), '{de}', '{para}'))").format(
        coluna="ementa", de=texto_busca.ACENTUADAS, para=texto_busca.SEM_ACENTO
    )
    assert modelo == texto_busca.sql_tsvector("ementa")
    assert "EXPRESSAO = \"to_tsvector('portuguese', translate(lower({coluna}), " in texto
    assert f'ACENTUADAS = "{texto_busca.ACENTUADAS}"' in texto
    assert f'SEM_ACENTO = "{texto_busca.SEM_ACENTO}"' in texto


def test_normalizacao_do_termo():
    assert texto_busca.palavras("  SAÚDE   Mental ") == "saude mental"
    assert texto_busca.normalizar("Ação Nº 5, Educação") == "acao nº 5, educacao"


def test_busca_por_numero(client, session):
    proposicao(session, "100", "PL", 2338, 2023, "Marco da inteligência artificial.")
    proposicao(session, "101", "PL", 2338, 2024, "Outro projeto de mesmo número.")
    proposicao(session, "102", "PEC", 2338, 2023, "Uma emenda.")
    proposicao(session, "103", "PL", 12, 2023, "Outro número.")
    for texto in ("PL 2338/2023", "pl 2338/2023", "PL nº 2.338, de 2023"):
        assert _rotulos(_busca(client, q=texto)) == ["PL 2338/2023"]
    # Sem sigla acha PL e PEC do mesmo número e ano.
    assert sorted(_rotulos(_busca(client, q="2338/2023"))) == ["PEC 2338/2023", "PL 2338/2023"]
    # Sem ano: o mais recente primeiro.
    assert _rotulos(_busca(client, q="pl 2338")) == ["PL 2338/2024", "PL 2338/2023"]
    assert _busca(client, q="PEC 2338")["total"] == 1


def test_busca_por_palavra_com_e_sem_acento(client, session):
    proposicao(session, "1", "PL", 1, 2025, "Institui a Política Nacional de Saúde Mental.")
    proposicao(session, "2", "PL", 2, 2025, "Dispõe sobre a saúde dos trabalhadores.")
    proposicao(session, "3", "PL", 3, 2025, "Cria o programa de educação financeira.")
    com = _busca(client, q="saúde mental")
    sem = _busca(client, q="saude mental")
    maiusculas = _busca(client, q="SAUDE MENTAL")
    assert _rotulos(com) == _rotulos(sem) == _rotulos(maiusculas) == ["PL 1/2025"]
    # Todas as palavras são exigidas; uma só acha as duas de saúde.
    assert _busca(client, q="saude")["total"] == 2
    assert _busca(client, q="educacao financeira")["total"] == 1
    assert _busca(client, q="educação  financeira")["total"] == 1
    assert _busca(client, q="saude espaco")["total"] == 0


def test_sem_busca_lista_tudo_e_pagina(client, session):
    for i in range(25):
        proposicao(
            session, str(i), "PL", i + 1, 2025, f"Projeto {i}.", data_apresentacao=date(2025, 1, 1)
        )
    pagina1 = _busca(client)
    assert (pagina1["total"], pagina1["pagina"], pagina1["por_pagina"]) == (25, 1, 20)
    assert len(pagina1["itens"]) == 20
    assert len(_busca(client, pagina=2)["itens"]) == 5
    assert _busca(client, pagina=3)["itens"] == []


def test_projeto_so_na_votacao_entra_com_rotulo_e_ementa(client, session):
    p = parlamentar(session, "Ana", "SC", "PXX")
    votacao(
        session,
        "9-1",
        "555",
        date(2026, 9, 3),
        {p.id: "Sim"},
        rotulo="PL 759/2015",
        ementa="Dispõe sobre a regulamentação da pesca.",
        resultado="aprovada",
        placar_sim=300,
        placar_nao=100,
    )
    # A mesma proposição existente em `proposicao` não duplica.
    proposicao(session, "777", "PL", 5, 2025, "Outra.")
    votacao(session, "9-2", "777", date(2026, 9, 4), rotulo="PL 5/2025", ementa="Outra.")
    corpo = _busca(client, q="PL 759/2015")
    item = corpo["itens"][0]
    assert corpo["total"] == 1
    assert item["rotulo"] == "PL 759/2015"
    assert item["link"] == "/projeto/camara/555"
    assert item["ultima_votacao"]["sim"] == 300
    assert item["ultima_votacao"]["nao"] == 100
    assert item["ultima_votacao"]["resultado"] == "aprovada"
    assert item["ultima_votacao"]["link"] == "/votacao/camara/9-1"
    # Por palavra, sem acento.
    assert _busca(client, q="regulamentacao pesca")["total"] == 1
    # Votada = tem votação nominal; a de 2025 também; filtro "sem" fica com nenhuma.
    assert _busca(client, votacao="sem")["total"] == 0
    assert _busca(client, votacao="com")["total"] == 2
    assert _busca(client, ano=2015)["total"] == 1


def test_placar_contado_quando_a_fonte_nao_publica(client, session):
    a, b, c = (parlamentar(session, n, "SC", "PXX") for n in ("A", "B", "C"))
    proposicao(session, "10", "PL", 10, 2026)
    votacao(session, "v1", "10", date(2026, 8, 1), {a.id: "Sim", b.id: "Sim", c.id: "Não"})
    item = _busca(client, q="PL 10/2026")["itens"][0]
    assert (item["ultima_votacao"]["sim"], item["ultima_votacao"]["nao"]) == (2, 1)


def test_cartao_usa_a_votacao_principal_e_mp_acha_mpv(client, session):
    a = parlamentar(session, "A", "SC", "PXX")
    proposicao(session, "20", "MPV", 1343, 2026, "Medida provisória.")
    votacao(session, "1-1", "20", date(2026, 8, 1), {a.id: "Sim"},
            descricao="Aprovada a Medida Provisória.")  # fmt: skip
    votacao(session, "1-2", "20", date(2026, 8, 2), {a.id: "Não"},
            descricao="Rejeitado o Recurso nº 2.")  # fmt: skip
    for q in ("MP 1343", "MP 1343/2026", "MPV 1343/2026"):
        corpo = _busca(client, q=q)
        assert corpo["total"] == 1, q
    item = _busca(client, q="MP 1343")["itens"][0]
    assert item["ultima_votacao"]["descricao"] == "Aprovada a Medida Provisória."
    assert item["ultima_votacao"]["link"] == "/votacao/camara/1-1"


def test_filtros_de_votacao_tema_ano_e_casa(client, session):
    proposicao(session, "1", "PL", 1, 2025, "Saúde.")
    proposicao(session, "2", "PL", 2, 2026, "Educação.")
    proposicao(session, "3", "PL", 3, 2026, "Senado educação.", casa="senado")
    votacao(session, "v1", "1", date(2026, 9, 1))
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="2", tema="Educação"))
    session.flush()
    assert _rotulos(_busca(client, votacao="com")) == ["PL 1/2025"]
    assert sorted(_rotulos(_busca(client, votacao="sem"))) == ["PL 2/2026", "PL 3/2026"]
    assert _rotulos(_busca(client, tema="Educação")) == ["PL 2/2026"]
    assert sorted(_rotulos(_busca(client, ano=2026))) == ["PL 2/2026", "PL 3/2026"]
    assert _rotulos(_busca(client, casa="senado")) == ["PL 3/2026"]
    assert _busca(client, esfera="estadual")["total"] == 0


def test_ordem_na_pauta_primeiro_e_depois_data(client, session):
    proposicao(session, "1", "PL", 1, 2025, data_apresentacao=date(2025, 1, 1))
    proposicao(session, "2", "PL", 2, 2025, data_apresentacao=date(2025, 6, 1))
    proposicao(session, "3", "PL", 3, 2025, data_apresentacao=date(2025, 3, 1))
    proposicao(session, "4", "PL", 4, 2025, data_apresentacao=date(2025, 2, 1))
    ing = ingestao(session, "camara_pauta")
    session.add(
        PautaItem(casa="camara", data=date(2026, 11, 5), sessao="s1", proposicao_id_externo="1",
                  ingestao_id=ing.id)
    )  # fmt: skip
    session.add(
        PautaItem(casa="camara", data=date(2026, 11, 3), sessao="s1", proposicao_id_externo="4",
                  ingestao_id=ing.id)
    )  # fmt: skip
    # Uma pauta passada não conta.
    session.add(
        PautaItem(casa="camara", data=date(2026, 9, 3), sessao="s0", proposicao_id_externo="2",
                  ingestao_id=ing.id)
    )  # fmt: skip
    # Tramitação recente puxa o projeto 3 para cima dos que não estão na pauta.
    session.add(
        Tramitacao(casa="camara", proposicao_id_externo="3", ordem=1,
                   data=date(2026, 10, 1), descricao="Algo.", ingestao_id=ing.id)
    )  # fmt: skip
    session.flush()
    corpo = projetos_busca.buscar(session, hoje=HOJE, ordem="recentes")
    assert [i["rotulo"] for i in corpo["itens"]] == [
        "PL 4/2025",
        "PL 1/2025",
        "PL 3/2025",
        "PL 2/2025",
    ]
    assert corpo["itens"][0]["na_pauta"] == date(2026, 11, 3)
    assert corpo["itens"][2]["na_pauta"] is None


def test_local_projeto_e_votacao_nao_ligada(client, session):
    vereadora = mandato_local(session, "Vera", "camara", "SC")
    deputada = mandato_local(session, "Dani", "assembleia", "AC")
    p_local = projeto_local(session, vereadora, "Projeto de Lei Ordinária", 7, 2026)
    p_estadual = projeto_local(
        session, deputada, "Projeto de Lei Complementar", 3, 2026, "Altera a saúde mental."
    )
    votacao_local(session, "camara", "SC", materia="Requerimento nº 62 de 2025")
    ligada = votacao_local(
        session, "camara", "SC", materia="Projeto de Lei nº 7/2026", projeto_local_id=p_local.id
    )
    votacao_local(
        session, "assembleia", "AC", materia="Veto nº 4 de 2026", materia_ementa="Veto total."
    )
    todos = _busca(client)
    # A votação ligada ao projeto aparece dentro do projeto, não como item à parte.
    assert todos["total"] == 4
    assert {i["tipo"] for i in todos["itens"]} == {"projeto_local", "votacao_local"}

    municipal = _busca(client, esfera="municipal")
    assert {i["casa"] for i in municipal["itens"]} == {"camara_municipal"}
    projeto = next(i for i in municipal["itens"] if i["tipo"] == "projeto_local")
    assert projeto["link"] == f"/projeto/local/{p_local.id}"
    assert projeto["municipio"] == "Florianópolis"
    assert projeto["uf"] == "SC"
    assert projeto["ultima_votacao"]["link"] == f"/votacao/local/{ligada.id}"
    assert projeto["situacao"] == "Em tramitação"

    estadual = _busca(client, esfera="estadual", uf="ac")
    assert {i["esfera"] for i in estadual["itens"]} == {"estadual"}
    assert _busca(client, casa="assembleia")["total"] == 3 - 1  # projeto + veto
    assert _busca(client, uf="SC")["total"] == 2
    assert _busca(client, municipio="4205407")["total"] == 2
    assert _busca(client, municipio="0000000")["total"] == 0

    # Por número: projeto de lei da vereadora, com e sem sigla.
    assert [i["link"] for i in _busca(client, q="PL 7/2026")["itens"]] == [
        f"/projeto/local/{p_local.id}"
    ]
    assert _busca(client, q="PLC 3/2026")["itens"][0]["link"] == f"/projeto/local/{p_estadual.id}"
    # Por palavra sem acento, a ementa do projeto local e a da votação.
    assert _busca(client, q="saude mental")["total"] == 2
    assert _busca(client, q="veto total")["itens"][0]["rotulo"] == "Veto nº 4 de 2026"
    # Votação local sem ementa e sem projeto: aparece com o texto da matéria.
    sem_ementa = next(i for i in todos["itens"] if i["rotulo"].startswith("Requerimento"))
    assert sem_ementa["ementa"] is None
    assert sem_ementa["link"].startswith("/votacao/local/")
    # Tema só existe no Congresso; "sem votação" tira as votações locais.
    assert _busca(client, tema="Educação")["total"] == 0
    assert [i["tipo"] for i in _busca(client, votacao="sem")["itens"]] == ["projeto_local"]
    assert _busca(client, votacao="com")["total"] == 3


def test_fontes_por_bloco_e_validacao(client, session):
    ingestao(session, "camara_votacoes", date(2026, 10, 19))
    ingestao(session, "camara_proposicoes", date(2026, 10, 20))
    corpo = _busca(client)
    nomes = [f["fonte_nome"] for f in corpo["fontes"]]
    assert len(nomes) == 3
    assert corpo["fontes"][0]["atualizado_em"].startswith("2026-10-19")
    assert corpo["fontes"][1]["atualizado_em"] is None
    assert client.get("/projetos", params={"esfera": "mundial"}).status_code == 422
    assert client.get("/projetos", params={"pagina": 0}).status_code == 422


def test_temas_dos_projetos_sem_classificacao_e_em_ordem(client, session):
    for casa, tema in [
        ("camara", "Saúde"),
        ("camara", "Educação"),
        ("camara", "Sem classificação"),
        ("senado", "Economia"),
        ("senado", "Saúde"),
    ]:
        session.add(ProposicaoTema(casa=casa, proposicao_id_externo="1", tema=tema))
    session.flush()
    todos = client.get("/projetos/temas").json()
    assert todos["temas"] == ["Economia", "Educação", "Saúde"]
    camara = client.get("/projetos/temas", params={"casa": "camara"}).json()
    assert (camara["casa"], camara["temas"]) == ("camara", ["Educação", "Saúde"])


def test_ids_dos_projetos_com_votacao_para_o_sitemap(client, session):
    proposicao(session, "1", "PL", 1, 2025, "Um.")
    proposicao(session, "2", "PL", 2, 2025, "Dois.")
    proposicao(session, "3", "PL", 3, 2025, "Sem votação.")
    votacao(session, "v1", "1", date(2026, 8, 1))
    votacao(session, "v1b", "1", date(2026, 9, 1))
    votacao(session, "v2", "2", date(2026, 10, 1))
    corpo = client.get("/projetos/ids", params={"votacao": "com"}).json()
    assert corpo["itens"] == [
        {"casa": "camara", "id_externo": "2", "data": "2026-10-01"},
        {"casa": "camara", "id_externo": "1", "data": "2026-09-01"},
    ]
    assert len(client.get("/projetos/ids", params={"limite": 1}).json()["itens"]) == 1


def _completo(session, ing):
    """PL 1/2026: votação, 2 discursos, 3 passos no caminho, situação e tema (nível 5)."""
    proposicao(session, "1", "PL", 1, 2026, situacao="Aguardando sanção",
               data_apresentacao=date(2026, 1, 10))  # fmt: skip
    votacao(session, "v1", "1", date(2026, 5, 1))
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="1", tema="Saúde"))
    for n in range(3):
        session.add(
            Tramitacao(casa="camara", proposicao_id_externo="1", ordem=n + 1,
                       data=datetime(2026, 6, 1), descricao="Andou.", ingestao_id=ing.id)
        )  # fmt: skip
    for n in range(2):
        session.add(
            Discurso(casa="camara", id_externo=f"d{n}", data=date(2026, 5, 1),
                     proposicao_id_externo="1", ingestao_id=ing.id)
        )  # fmt: skip
    session.flush()


def test_ordem_padrao_por_informacao_publicada(client, session):
    ing = ingestao(session, "camara_tramitacao")
    _completo(session, ing)
    # Votação mais recente que a do PL 1, mas só votação, situação e tema (nível 3).
    proposicao(session, "2", "PL", 2, 2026, situacao="Em comissão",
               data_apresentacao=date(2026, 1, 5))  # fmt: skip
    votacao(session, "v2", "2", date(2026, 9, 1))
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="2", tema="Educação"))
    # "Sem classificação" não conta como tema.
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="2", tema="Sem classificação"))
    # Votação local com ementa e resultado (nível 3), votada depois do PL 2: vem antes dele.
    votacao_local(session, "camara", "SC", materia="Projeto de Lei nº 9/2026",
                  materia_ementa="Cria a feira.", data=date(2026, 9, 10))  # fmt: skip
    # Sem votação: situação e tema (nível 2), apresentado há pouco.
    proposicao(session, "3", "PL", 3, 2026, situacao="Aguardando parecer",
               data_apresentacao=date(2026, 10, 1))  # fmt: skip
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="3", tema="Saúde"))
    # Nada além da ementa (nível 0), o mais recente de todos.
    proposicao(session, "4", "PL", 4, 2026, data_apresentacao=date(2026, 10, 15))
    session.flush()

    corpo = _busca(client)
    assert corpo["ordem"] == "informacao"
    assert _rotulos(corpo) == [
        "PL 1/2026",
        "Projeto de Lei nº 9/2026",
        "PL 2/2026",
        "PL 3/2026",
        "PL 4/2026",
    ]
    assert [i["nivel_informacao"] for i in corpo["itens"]] == [5, 3, 3, 2, 0]
    primeiro = corpo["itens"][0]
    assert (primeiro["discursos"], primeiro["passos_caminho"]) == (2, 3)
    assert (corpo["itens"][2]["discursos"], corpo["itens"][2]["passos_caminho"]) == (0, 0)
    # Itens locais não têm discursos nem caminho.
    assert (corpo["itens"][1]["discursos"], corpo["itens"][1]["passos_caminho"]) == (None, None)

    # A mesma regra vale com busca e filtro.
    assert _rotulos(_busca(client, esfera="federal", ano=2026)) == [
        "PL 1/2026", "PL 2/2026", "PL 3/2026", "PL 4/2026",
    ]  # fmt: skip
    # "recentes": a data da última votação ou movimentação, da mais nova para a mais antiga.
    recentes = _busca(client, ordem="recentes")
    assert recentes["ordem"] == "recentes"
    assert _rotulos(recentes) == [
        "PL 4/2026",
        "PL 3/2026",
        "Projeto de Lei nº 9/2026",
        "PL 2/2026",
        "PL 1/2026",
    ]
    assert client.get("/projetos", params={"ordem": "relevancia"}).status_code == 422


def test_cobertura_da_cidade_e_do_estado(client, session):
    # Florianópolis tem câmara carregada; Gaspar não, mas tem o site da câmara no catálogo.
    mandato_local(session, "Vera", "camara", "SC", "4205407")
    municipio(session, "4205902", "Gaspar", "SC")
    session.add(CanalOficial(municipio_ibge="4205902", tipo="prefeitura",
                             url="https://gaspar.sc.gov.br/"))  # fmt: skip
    session.add(CanalOficial(municipio_ibge="4205902", tipo="camara",
                             url="https://camaragaspar.sc.gov.br/"))  # fmt: skip
    session.flush()

    assert _busca(client)["cobertura"] is None
    gaspar = _busca(client, uf="SC", municipio="4205902")
    assert gaspar["total"] == 0
    assert gaspar["cobertura"] == {
        "uf": "SC",
        "camara": {
            "municipio_ibge": "4205902",
            "municipio": "Gaspar",
            "tem_dados": False,
            "canal_url": "https://camaragaspar.sc.gov.br/",
        },
        "assembleia": {"uf": "SC", "tem_dados": False},
    }
    mandato_local(session, "Dani", "assembleia", "SC")
    floripa = _busca(client, municipio="4205407")
    assert floripa["cobertura"]["uf"] == "SC"  # vem do município
    assert floripa["cobertura"]["camara"]["tem_dados"] is True
    assert floripa["cobertura"]["camara"]["canal_url"] is None
    assert floripa["cobertura"]["assembleia"]["tem_dados"] is True
    so_estado = _busca(client, uf="sc")["cobertura"]
    assert so_estado["camara"] is None
    assert so_estado["assembleia"] == {"uf": "SC", "tem_dados": True}
