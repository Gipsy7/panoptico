from app.models import ProposicaoTema
from app.services import presenca, votos_tema
from tests.test_votos import _cenario


def _temas(session):
    """v0 Saúde | v1 Saúde e Educação (dois temas) | v2 Educação | v3 Saúde e Economia."""
    pares = [
        ("0", "Saúde"), ("1", "Saúde"), ("1", "Educação"), ("2", "Educação"),
        ("3", "Saúde"), ("3", "Economia"),
    ]  # fmt: skip
    for prop, tema in pares:
        session.add(ProposicaoTema(casa="camara", proposicao_id_externo=prop, tema=tema))
    session.flush()


def _por_tema(session, p):
    return {t["tema"]: t for t in votos_tema.votos_por_tema(session, p, 2026)["temas"]}


def test_contagens_media_com_zero_e_voto_em_dois_temas(session):
    a, b, c = _cenario(session)
    _temas(session)
    assert all(p.em_exercicio for p in (a, b, c))

    t = _por_tema(session, a)
    # Saúde: v0, v1, v3. A votou nas três (Obstrução conta como voto).
    assert (t["Saúde"]["total_votacoes"], t["Saúde"]["votou"]) == (3, 3)
    # C votou em v0 e v1 e faltou em v3: 2 de 3. Média: (100 + 100 + 66,7) / 3.
    assert t["Saúde"]["media_casa_percentual"] == 88.9
    assert t["Saúde"]["media_casa_votou"] == 2.7
    # A votação v1 conta em Saúde e em Educação.
    assert (t["Educação"]["total_votacoes"], t["Educação"]["votou"]) == (2, 2)
    # Economia (só v3): C não votou e entra com zero na média: (100 + 100 + 0) / 3.
    assert (t["Economia"]["total_votacoes"], t["Economia"]["votou"]) == (1, 1)
    assert t["Economia"]["media_casa_percentual"] == 66.7
    assert t["Economia"]["media_casa_votou"] == 0.7

    tc = _por_tema(session, c)
    assert (tc["Saúde"]["votou"], tc["Saúde"]["percentual"]) == (2, 66.7)
    assert tc["Economia"]["votou"] == 0

    # Alinhamento com o Governo: A em Saúde = v0 igual, v1 diferente, v3 igual.
    assert (t["Saúde"]["governo_iguais"], t["Saúde"]["governo_total"]) == (2, 3)
    # Educação: v1 (Governo Não, A votou Sim) conta; v2 (Liberado) fica fora.
    assert (t["Educação"]["governo_iguais"], t["Educação"]["governo_total"]) == (0, 1)


def test_ordem_por_numero_de_votacoes(session):
    a, _, _ = _cenario(session)
    _temas(session)
    temas = votos_tema.votos_por_tema(session, a, 2026)["temas"]
    assert [t["tema"] for t in temas] == ["Saúde", "Educação", "Economia"]


def test_soma_bate_com_a_presenca_quando_cada_votacao_tem_um_tema(session):
    a, b, c = _cenario(session)
    for i in range(4):
        session.add(ProposicaoTema(casa="camara", proposicao_id_externo=str(i), tema=f"T{i % 2}"))
    session.flush()
    for p in (a, b, c):
        temas = votos_tema.votos_por_tema(session, p, 2026)["temas"]
        geral = presenca.resumo(session, p, 2026)
        assert sum(t["votou"] for t in temas) == geral["votou"]
        assert sum(t["total_votacoes"] for t in temas) == geral["total_votacoes"]


def test_rota(client, session):
    a, _, _ = _cenario(session)
    _temas(session)
    session.commit()
    r = client.get(f"/parlamentares/{a.id}/votos-por-tema")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["ano"] == 2026 and corpo["temas"][0]["tema"] == "Saúde"
    assert client.get(f"/parlamentares/{a.id}/votos-por-tema?ano=1999").status_code == 404


def test_votacao_secreta_com_voto_em_branco_conta_como_votou_no_tema(session):
    from datetime import date

    from sqlalchemy import select

    from app.models import Parlamentar
    from ingestion import votacoes_comum as vc
    from tests.test_api import _ingestao, _popular

    _popular(session)
    d = session.scalars(select(Parlamentar).where(Parlamentar.casa == "camara")).all()[0]
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="P1", tema="Economia"))
    votacoes = [
        {
            "id_externo": "s",
            "data": date(2026, 2, 1),
            "descricao": "x",
            "proposicao": "PDL 1",
            "proposicao_id_externo": "P1",
            "secreta": True,
        }
    ]
    votos = [{"id_externo_votacao": "s", "parlamentar_id": d.id, "voto": ""}]
    vc.recarregar_votacoes(session, "camara", 2026, votacoes, votos, _ingestao(session))
    session.flush()
    t = _por_tema(session, d)["Economia"]
    assert (t["total_votacoes"], t["votou"]) == (1, 1)


def test_sem_classificacao_fica_fora_e_fora_de_exercicio_nao_entra_na_media(session):
    from datetime import date

    from ingestion.proposicoes_comum import SEM_CLASSIFICACAO

    a, b, c = _cenario(session)
    _temas(session)
    session.add(ProposicaoTema(casa="camara", proposicao_id_externo="2", tema=SEM_CLASSIFICACAO))
    c.em_exercicio = False
    b.em_exercicio_desde = date(2026, 3, 3)  # só v2 (03/03) e v3 (04/03) contam para B
    session.flush()

    t = _por_tema(session, a)
    assert SEM_CLASSIFICACAO not in t
    # Economia (só v3): A e B votaram; C saiu do exercício e não entra na média.
    assert t["Economia"]["media_casa_percentual"] == 100.0
    # Saúde: A 3 de 3 e B 1 de 1 (só v3 depois da posse): média 100.
    assert t["Saúde"]["media_casa_percentual"] == 100.0
    tb = _por_tema(session, b)
    assert (tb["Saúde"]["total_votacoes"], tb["Saúde"]["votou"]) == (1, 1)
    assert "Economia" in tb and tb["Educação"]["total_votacoes"] == 1  # v2
    # Quem saiu do exercício ainda vê os próprios números.
    tc = _por_tema(session, c)
    assert (tc["Economia"]["votou"], tc["Economia"]["percentual"]) == (0, 0.0)


def test_senado_tira_o_na_do_total(session):
    from datetime import date

    from sqlalchemy import select

    from app.models import Parlamentar
    from ingestion import votacoes_comum as vc
    from tests.test_api import _ingestao, _popular

    _popular(session)
    a, b, c = session.scalars(
        select(Parlamentar).where(Parlamentar.casa == "senado").order_by(Parlamentar.id)
    ).all()
    for p in (a, b, c):
        p.em_exercicio, p.em_exercicio_desde = True, None
    session.add(ProposicaoTema(casa="senado", proposicao_id_externo="S", tema="Economia"))
    votacoes = [
        {"id_externo": f"s{i}", "data": date(2026, 4, i + 1), "descricao": "x",
         "proposicao": "PL 1/2026", "proposicao_id_externo": "S", "secreta": False}
        for i in range(2)
    ]  # fmt: skip
    votos = [
        {"id_externo_votacao": "s0", "parlamentar_id": a.id, "voto": "Sim"},
        {"id_externo_votacao": "s1", "parlamentar_id": a.id, "voto": "Não"},
        {"id_externo_votacao": "s0", "parlamentar_id": b.id, "voto": "NA"},
        {"id_externo_votacao": "s1", "parlamentar_id": b.id, "voto": "Sim"},
    ]  # C não votou em nenhuma
    vc.recarregar_votacoes(session, "senado", 2026, votacoes, votos, _ingestao(session))
    session.flush()

    tb = _por_tema(session, b)["Economia"]
    assert (tb["total_votacoes"], tb["votou"], tb["percentual"]) == (1, 1, 100.0)
    # Média: A 100, B 100 (o NA saiu do total), C 0.
    assert tb["media_casa_percentual"] == 66.7
