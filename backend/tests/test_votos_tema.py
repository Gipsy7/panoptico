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
