from collections import Counter
from datetime import date

from sqlalchemy import select

from app.models import Parlamentar, ProposicaoTema
from app.services import ranking, votos
from ingestion import proposicoes_comum as pc
from ingestion import resumos
from ingestion import votacoes_comum as vc
from tests.test_api import _ingestao, _popular


def test_maioria_dos_outros():
    # Tira o próprio voto antes de contar.
    assert votos.maioria_dos_outros(Counter({"Sim": 3, "Não": 1}), "Sim") == "Sim"
    assert votos.maioria_dos_outros(Counter({"Sim": 2, "Não": 2}), "Sim") == "Não"
    # Empate entre os outros: sem maioria.
    assert votos.maioria_dos_outros(Counter({"Sim": 2, "Não": 1}), "Sim") is None
    # Menos de 2 outros votando: sem maioria (partido de um deputado só, por exemplo).
    assert votos.maioria_dos_outros(Counter({"Sim": 2}), "Sim") is None
    assert votos.maioria_dos_outros(Counter({"Sim": 1}), "Sim") is None


def _cenario(session):
    """3 deputados (A e B do PL, C do PT) e 4 votações com orientação do Governo:
    v0 Governo Sim  | A Sim  B Sim  C Não
    v1 Governo Não  | A Sim  B Não  C Não
    v2 Liberado     | A Sim  B Sim  C Sim   (fora do alinhamento com o Governo)
    v3 Obstrução    | A Obstrução  B Sim    (C ausente)
    """
    _popular(session)
    a, b, c = session.scalars(
        select(Parlamentar).where(Parlamentar.casa == "camara").order_by(Parlamentar.id)
    ).all()
    votacoes = [
        {"id_externo": f"v{i}", "data": date(2026, 3, i + 1), "descricao": "x",
         "proposicao": f"PL {i}/2026", "proposicao_id_externo": str(i), "secreta": False}
        for i in range(4)
    ]  # fmt: skip
    tabela = {
        "v0": {a: "Sim", b: "Sim", c: "Não"},
        "v1": {a: "Sim", b: "Não", c: "Não"},
        "v2": {a: "Sim", b: "Sim", c: "Sim"},
        "v3": {a: "Obstrução", b: "Sim"},
    }
    partido = {a: "PL", b: "PL", c: "PT"}
    lista_votos = [
        {"id_externo_votacao": v, "parlamentar_id": p.id, "voto": voto, "partido": partido[p]}
        for v, linha in tabela.items()
        for p, voto in linha.items()
    ]
    orientacoes = [
        {"id_externo_votacao": "v0", "bancada": "Governo", "orientacao": "Sim"},
        {"id_externo_votacao": "v1", "bancada": "Governo", "orientacao": "Não"},
        {"id_externo_votacao": "v2", "bancada": "Governo", "orientacao": "Liberado"},
        {"id_externo_votacao": "v3", "bancada": "Governo", "orientacao": "Obstrução"},
    ]
    vc.recarregar_votacoes(
        session, "camara", 2026, votacoes, lista_votos, _ingestao(session), orientacoes
    )
    session.flush()
    return a, b, c


def test_alinhamento_com_o_governo(session):
    a, b, c = _cenario(session)
    al = votos.alinhamentos(session, "camara", 2026)
    # A: v0 igual, v1 diferente, v3 igual (Obstrução) -> 2 de 3
    assert (al[a.id]["governo"].iguais, al[a.id]["governo"].total) == (2, 3)
    # B: v0 igual, v1 igual, v3 diferente -> 2 de 3
    assert (al[b.id]["governo"].iguais, al[b.id]["governo"].total) == (2, 3)
    # C: v0 diferente, v1 igual, ausente em v3 -> 1 de 2
    assert (al[c.id]["governo"].iguais, al[c.id]["governo"].total) == (1, 2)
    # Partidos com um só "outro" deputado votando não formam maioria.
    assert al[a.id]["partido"].total == 0


def test_lista_de_votos_e_convergencia(session):
    a, b, c = _cenario(session)
    lista = votos.lista_votos(session, a, 2026, None, 1)
    assert lista["total"] == 4
    assert lista["itens"][0]["proposicao"] == "PL 3/2026"  # mais recente primeiro
    assert lista["itens"][0]["orientacao_governo"] == "Obstrução"

    conv = votos.convergencia(session, a, b, 2026)
    # Votaram juntos em v0..v3; iguais em v0 e v2.
    assert (conv["votacoes_em_comum"], conv["iguais"], conv["percentual"]) == (4, 2, 50.0)
    assert [d["proposicao"] for d in conv["divergencias"]] == ["PL 3/2026", "PL 1/2026"]
    # C não votou em v3: só 3 votações em comum com A.
    assert votos.convergencia(session, a, c, 2026)["votacoes_em_comum"] == 3


def test_resumo_e_lista_ordenavel(client, session):
    a, b, c = _cenario(session)
    session.execute(resumos.ResumoParlamentar.__table__.insert(), resumos.calcular(session, [2026]))
    session.flush()

    por_nome = client.get("/parlamentares?casa=camara").json()
    nomes = [i["nome_parlamentar"] for i in por_nome["itens"]]
    assert nomes == sorted(nomes, key=ranking.chave_nome)

    por_governo = client.get("/parlamentares?casa=camara&ordenar=governo&ordem=desc").json()
    assert [i["governo"] for i in por_governo["itens"]] == [66.7, 66.7, 50.0]

    # No critério "governo", senadores ficam por último (não se aplica a eles).
    todos = client.get("/parlamentares?ordenar=governo&ordem=desc").json()["itens"]
    assert [i["casa"] for i in todos][-3:] == ["senado"] * 3

    alvo = a.nome_parlamentar.split()[0].lower()
    busca = client.get(f"/parlamentares?busca={alvo}").json()
    assert a.id in [i["id"] for i in busca["itens"]]
    assert client.get("/parlamentares?ano=1999").status_code == 404
    assert client.get("/parlamentares?ordenar=nota").status_code == 422


def test_rota_de_votos_do_perfil(client, session):
    a, b, c = _cenario(session)
    session.execute(resumos.ResumoParlamentar.__table__.insert(), resumos.calcular(session, [2026]))
    session.execute(
        ProposicaoTema.__table__.insert(),
        [{"casa": "camara", "proposicao_id_externo": "1", "tema": "Economia"}],
    )
    session.flush()

    corpo = client.get(f"/parlamentares/{a.id}/votos").json()
    assert corpo["governo"] == {"iguais": 2, "total": 3, "percentual": 66.7}
    assert corpo["total"] == 4
    assert corpo["temas_disponiveis"] == ["Economia"]

    so_economia = client.get(f"/parlamentares/{a.id}/votos?tema=Economia").json()
    assert [i["proposicao"] for i in so_economia["itens"]] == ["PL 1/2026"]
    assert so_economia["itens"][0]["temas"] == ["Economia"]


def test_rota_de_temas_do_perfil(client, session):
    _popular(session)
    deputado = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).first()
    senador = session.scalars(select(Parlamentar).where(Parlamentar.casa == "senado")).first()
    ingestao = _ingestao(session)
    base = {"ementa": "E.", "situacao": None, "virou_lei": False, "url": "u", "ano": 2024,
            "sigla_tipo": "PL", "data_apresentacao": date(2024, 1, 1)}  # fmt: skip
    mapa = pc.upsert_proposicoes(
        session,
        "camara",
        [{**base, "id_externo": "p1", "numero": 1}, {**base, "id_externo": "p2", "numero": 2}],
        ingestao,
    )
    pc.substituir_autorias(
        session,
        list(mapa.values()),
        [
            {"proposicao_id": mapa["p1"], "parlamentar_id": deputado.id, "primeiro_autor": True},
            {"proposicao_id": mapa["p2"], "parlamentar_id": deputado.id, "primeiro_autor": False},
        ],
    )
    session.execute(
        ProposicaoTema.__table__.insert(),
        [
            {"casa": "camara", "proposicao_id_externo": "p1", "tema": "Saúde"},
            {"casa": "camara", "proposicao_id_externo": "p1", "tema": resumos.TEMA_HOMENAGENS},
            {"casa": "camara", "proposicao_id_externo": "p2", "tema": "Saúde"},
        ],
    )
    session.flush()

    corpo = client.get(f"/parlamentares/{deputado.id}/temas").json()
    assert corpo["temas"][0] == {"tema": "Saúde", "primeiro_autor": 1, "coautor": 1}
    assert corpo["homenagens"] == 1
    # Senador sem projetos classificados: lista vazia (o Senado também tem temas).
    assert client.get(f"/parlamentares/{senador.id}/temas").json()["temas"] == []


def test_rota_comparar(client, session):
    a, b, c = _cenario(session)
    senador = session.scalars(select(Parlamentar).where(Parlamentar.casa == "senado")).first()
    session.execute(resumos.ResumoParlamentar.__table__.insert(), resumos.calcular(session, [2026]))
    session.flush()

    corpo = client.get(f"/comparar?a={a.id}&b={b.id}").json()
    assert corpo["mesma_casa"] is True
    assert corpo["convergencia"]["votacoes_em_comum"] == 4
    assert corpo["convergencia"]["percentual"] == 50.0
    assert corpo["numeros_a"]["governo"] == 66.7

    misto = client.get(f"/comparar?a={a.id}&b={senador.id}").json()
    assert misto["mesma_casa"] is False
    assert misto["convergencia"] is None

    assert client.get(f"/comparar?a={a.id}&b={a.id}").status_code == 422
    assert client.get(f"/comparar?a={a.id}&b=999999").status_code == 404


def test_votos_nas_comissoes_ficam_fora_do_plenario(client, session):
    from datetime import date

    from app.models import FonteIngestao, Parlamentar, Votacao
    from ingestion import votacoes_comum as vc
    from tests.test_api import _popular

    _popular(session)
    deputado = session.query(Parlamentar).filter_by(casa="camara").first()
    ingestao = FonteIngestao(fonte="t", url="u", arquivo_raw="r")
    session.add(ingestao)
    session.flush()
    votacoes = [
        {"id_externo": "c1", "orgao_sigla": "CCJC", "orgao_nome": "Comissão de Constituição",
         "data": date(2026, 3, 1), "descricao": "Aprovado o parecer"},
    ]  # fmt: skip
    votos = [{"id_externo_votacao": "c1", "parlamentar_id": deputado.id, "voto": "Sim"}]
    assert vc.recarregar_comissoes(session, "camara", 2026, votacoes, votos, ingestao) == 1
    # Ano sem votação nominal em comissão só limpa, sem erro.
    assert vc.recarregar_comissoes(session, "camara", 2025, [], [], ingestao) == 0
    session.flush()

    corpo = client.get(f"/parlamentares/{deputado.id}/votos-comissoes").json()
    assert corpo["total"] == 1
    assert corpo["comissoes"] == [
        {"sigla": "CCJC", "nome": "Comissão de Constituição", "votacoes": 1}
    ]
    assert corpo["itens"][0]["voto"] == "Sim"
    assert session.query(Votacao).count() == 0  # o Plenário não foi tocado
