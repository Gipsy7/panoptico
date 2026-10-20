"""Lista de parlamentares (app/services/ranking.py): percentuais, médias por Casa e por
partido, ano sem dados e o cache da base em modo serverless."""

from datetime import UTC, datetime

import pytest

from app.config import settings
from app.models import Parlamentar, ResumoParlamentar
from app.services import ranking


def _parl(session, casa, ext, nome, partido="PL", uf="AC", em_exercicio=True):
    p = Parlamentar(
        casa=casa, id_externo=ext, nome_parlamentar=nome, partido=partido, uf=uf,
        fonte_url="https://x", atualizado_em=datetime(2026, 1, 1, tzinfo=UTC),
        em_exercicio=em_exercicio,
    )  # fmt: skip
    session.add(p)
    session.flush()
    return p


def _resumo(session, p, ano, **campos):
    session.add(ResumoParlamentar(parlamentar_id=p.id, ano=ano, **campos))
    session.flush()


@pytest.fixture(autouse=True)
def _sem_cache(monkeypatch):
    monkeypatch.setattr(settings, "serverless", False)
    ranking._cache.clear()
    yield
    ranking._cache.clear()


def test_pct_com_total_zero_e_arredondamento():
    assert ranking._pct(0, 0) is None
    assert ranking._pct(5, 0) is None
    assert ranking._pct(1, 3) == 33.3
    assert ranking._pct(0, 4) == 0.0


def test_medias_por_casa_ignora_quem_nao_tem_o_dado():
    itens = [
        {"casa": "camara", "gastos": 100.0, "presenca": 50.0, "projetos": 2, "normas": 0,
         "emendas": 10.0, "governo": 80.0},
        {"casa": "camara", "gastos": 200.0, "presenca": None, "projetos": 3, "normas": 1,
         "emendas": 20.0, "governo": None},
        {"casa": "senado", "gastos": 1000.0, "presenca": 90.0, "projetos": 1, "normas": 1,
         "emendas": 0.0, "governo": None},
    ]  # fmt: skip
    m = ranking.medias(itens)
    assert set(m) == {"camara", "senado"}
    assert "nome" not in m["camara"]
    assert m["camara"]["gastos"] == 150.0
    assert m["camara"]["presenca"] == 50.0  # o None não puxa a média para baixo
    assert m["camara"]["projetos"] == 2.5
    assert m["senado"]["governo"] is None  # ninguém tem o dado
    assert m["senado"]["gastos"] == 1000.0


def test_medias_com_casa_vazia():
    m = ranking.medias([])
    assert all(v is None for casa in m.values() for v in casa.values())


def test_media_partido_so_em_exercicio_da_casa_e_do_ano(session):
    a = _parl(session, "camara", "1", "A")
    b = _parl(session, "camara", "2", "B")
    fora = _parl(session, "camara", "3", "C", em_exercicio=False)
    sem_base = _parl(session, "camara", "4", "D")
    sen = _parl(session, "senado", "5", "E")
    _resumo(session, a, 2026, partido_iguais=9, partido_total=10)  # 90%
    _resumo(session, b, 2026, partido_iguais=1, partido_total=2)  # 50%
    _resumo(session, fora, 2026, partido_iguais=0, partido_total=10)
    _resumo(session, sem_base, 2026, partido_iguais=0, partido_total=0)  # sem votação: fora
    _resumo(session, sen, 2026, partido_iguais=0, partido_total=10)
    _resumo(session, a, 2025, partido_iguais=0, partido_total=10)
    assert ranking.media_partido(session, "camara", 2026) == 70.0
    assert ranking.media_partido(session, "senado", 2026) == 0.0
    assert ranking.media_partido(session, "camara", 2024) is None


def test_listar_ano_sem_dados(session):
    a = _parl(session, "camara", "1", "A")
    _resumo(session, a, 2025, gastos=10)
    r = ranking.listar(session, ano=2026)
    assert r["total"] == 0 and r["itens"] == []
    assert r["por_casa"] == {"camara": 0, "senado": 0}
    assert r["partidos"] == []
    assert all(v is None for casa in r["medias"].values() for v in casa.values())
    assert r["anos_disponiveis"] == [2025]
    assert r["atualizado_em"] is None


def test_listar_filtros_e_quem_nao_tem_o_dado_vai_para_o_fim(session):
    a = _parl(session, "camara", "1", "Bruno", partido="pl", uf="SP")
    b = _parl(session, "camara", "2", "Álvaro", partido="PT", uf="SP")
    c = _parl(session, "senado", "3", "Carla", partido="PL", uf="RJ")
    _parl(session, "camara", "4", "Fora", em_exercicio=False)
    _resumo(session, a, 2026, governo_iguais=1, governo_total=4, gastos=50)
    _resumo(session, b, 2026, governo_iguais=3, governo_total=4, gastos=50)
    _resumo(session, c, 2026, gastos=999)  # sem orientação do Governo

    nomes = lambda r: [i["nome_parlamentar"] for i in r["itens"]]  # noqa: E731
    assert nomes(ranking.listar(session, ano=2026)) == ["Álvaro", "Bruno", "Carla"]
    desc = ranking.listar(session, ano=2026, ordenar="governo", ordem="desc")
    assert nomes(desc) == ["Álvaro", "Bruno", "Carla"]
    asc = ranking.listar(session, ano=2026, ordenar="governo", ordem="asc")
    assert nomes(asc) == ["Bruno", "Álvaro", "Carla"]  # sem dado no fim nos dois sentidos
    # Empate no critério: desempate pelo nome.
    assert nomes(ranking.listar(session, ano=2026, ordenar="gastos", casa="camara")) == [
        "Álvaro",
        "Bruno",
    ]
    assert nomes(ranking.listar(session, ano=2026, uf="sp", partido="PL")) == ["Bruno"]
    assert nomes(ranking.listar(session, ano=2026, busca="alvaro")) == ["Álvaro"]


def test_listar_com_cache_nao_altera_a_base(session, monkeypatch):
    monkeypatch.setattr(settings, "serverless", True)
    for ext, nome, gastos in (("1", "Zeca", 1), ("2", "Ana", 3), ("3", "Mia", 2)):
        _resumo(session, _parl(session, "camara", ext, nome), 2026, gastos=gastos)
    ranking.listar(session, ano=2026)
    base = [i["id"] for i in ranking._cache[2026][1][0]]
    desc = ranking.listar(session, ano=2026, ordenar="gastos", ordem="desc")
    assert [i["nome_parlamentar"] for i in desc["itens"]] == ["Ana", "Mia", "Zeca"]
    # A ordenação devolvida não reordenou a base guardada em cache.
    assert [i["id"] for i in ranking._cache[2026][1][0]] == base
    # Enquanto o cache vale, um resumo novo no banco não aparece (mesma base).
    _resumo(session, _parl(session, "camara", "4", "Bia"), 2026)
    assert ranking.listar(session, ano=2026)["total"] == 3
    monkeypatch.setattr(settings, "serverless", False)
    assert ranking.listar(session, ano=2026)["total"] == 4
