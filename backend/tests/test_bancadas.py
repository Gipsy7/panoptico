from datetime import UTC, date, datetime

from app.models import Candidatura, FonteIngestao, MandatoLocal, Municipio, Parlamentar
from tests.test_api import _ingestao

ANO = date.today().year
AGORA = datetime(2026, 11, 1, tzinfo=UTC)


def _parl(session, ing, casa, n, partido, uf="SC", em_exercicio=True):
    p = Parlamentar(
        casa=casa,
        id_externo=f"{casa}{uf}{n}{partido}",
        nome_parlamentar=f"Nome {n}",
        partido=partido,
        uf=uf,
        em_exercicio=em_exercicio,
        fonte_url="https://x",
        atualizado_em=AGORA,
        ingestao_id=ing.id,
    )
    session.add(p)
    session.flush()
    return p


def _cand(session, ing, cargo, partido, n, ano=ANO, uf="SC", situacao="ELEITO POR QP", **campos):
    c = Candidatura(
        ano_eleicao=ano,
        sq_candidato=f"{cargo[:3]}{ano}{uf}{partido}{n}",
        cargo=cargo,
        uf=uf,
        unidade="x",
        nome=f"C{n}",
        nome_urna=f"C{n}",
        partido=partido,
        situacao_turno=situacao,
        ingestao_id=ing.id,
        **campos,
    )
    session.add(c)
    session.flush()
    return c


def _ok(session, fonte):
    ing = FonteIngestao(fonte=fonte, url="u", arquivo_raw="x", status="ok", concluido_em=AGORA)
    session.add(ing)
    session.flush()


def test_bancadas_do_estado_ordena_e_filtra_uf(client, session):
    ing = _ingestao(session)
    for i, p in enumerate(["PL", "PT", "PL", "PL", "MDB", "PT"]):
        _parl(session, ing, "camara", i, p)
    _parl(session, ing, "camara", 9, "PL", uf="RS")
    _parl(session, ing, "camara", 10, "NOVO", em_exercicio=False)
    _parl(session, ing, "senado", 1, None)
    _ok(session, "camara_deputados")
    corpo = client.get("/estados/sc/bancadas").json()
    assert corpo["camara_uf"]["itens"] == [
        {"partido": "PL", "n": 3},
        {"partido": "PT", "n": 2},
        {"partido": "MDB", "n": 1},
    ]
    assert corpo["camara_uf"]["total"] == 6
    assert corpo["camara_uf"]["atualizado_em"] is not None
    assert corpo["senado_uf"]["itens"] == [{"partido": "Sem partido", "n": 1}]
    assert corpo["assembleia"]["itens"] == []
    assert client.get("/estados/xx/bancadas").status_code == 404


def test_assembleia_usa_mandato_local_e_cai_no_tse(client, session):
    ing = _ingestao(session)
    _cand(session, ing, "DEPUTADO ESTADUAL", "PP", 1, ano=ANO - 4)
    _cand(session, ing, "DEPUTADO ESTADUAL", "PP", 2, ano=ANO - 4)
    _cand(session, ing, "DEPUTADO ESTADUAL", "PT", 3, ano=ANO - 4)
    _cand(session, ing, "DEPUTADO ESTADUAL", "NOVO", 4, ano=ANO)  # ainda sem posse
    a = client.get("/estados/sc/bancadas").json()["assembleia"]
    assert a["origem"] == "tse"
    assert a["itens"] == [{"partido": "PP", "n": 2}, {"partido": "PT", "n": 1}]
    assert str(ANO - 4) in a["fonte_nome"]

    for i, p in enumerate(["PSD", "PSD", "PL"]):
        session.add(
            MandatoLocal(
                casa="assembleia",
                uf="SC",
                id_externo=str(i),
                nome=f"D{i}",
                partido=p,
                em_exercicio=True,
                sapl_url="https://alesc.exemplo",
            )
        )
    session.flush()
    a = client.get("/estados/sc/bancadas").json()["assembleia"]
    assert a["origem"] == "assembleia"
    assert a["itens"] == [{"partido": "PSD", "n": 2}, {"partido": "PL", "n": 1}]


def test_bancada_do_municipio(client, session):
    ing = _ingestao(session)
    session.add(Municipio(ibge="4205407", nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.flush()
    assert client.get("/municipios/0000000/bancada").status_code == 404
    _cand(session, ing, "VEREADOR", "MDB", 1, ano=2024, municipio_ibge="4205407")
    _cand(session, ing, "VEREADOR", "MDB", 2, ano=2024, municipio_ibge="4205407")
    _cand(session, ing, "VEREADOR", "PL", 3, ano=2024, municipio_ibge="4205407")
    _cand(
        session, ing, "VEREADOR", "PL", 4, ano=2024, municipio_ibge="4205407", situacao="SUPLENTE"
    )
    corpo = client.get("/municipios/4205407/bancada").json()
    assert corpo["origem"] == "tse"
    assert corpo["total"] == 3
    assert corpo["itens"][0] == {"partido": "MDB", "n": 2}
    session.add(
        MandatoLocal(
            casa="camara",
            uf="SC",
            municipio_ibge="4205407",
            id_externo="1",
            nome="V",
            partido="PSD",
            em_exercicio=True,
            sapl_url="https://camara.exemplo",
        )
    )
    session.flush()
    corpo = client.get("/municipios/4205407/bancada").json()
    assert corpo["origem"] == "camara"
    assert corpo["itens"] == [{"partido": "PSD", "n": 1}]


def test_composicao_camara_soma_513_com_dados_completos(client, session):
    ing = _ingestao(session)
    distribuicao = {"PL": 300, "PT": 150, "MDB": 63}
    n = 0
    for partido, q in distribuicao.items():
        for _ in range(q):
            _parl(session, ing, "camara", n, partido, uf="SP")
            n += 1
    n = 0
    for partido, q in {"PL": 250, "PT": 200, "PSD": 63}.items():
        for _ in range(q):
            _cand(session, ing, "DEPUTADO FEDERAL", partido, n, uf="SP")
            n += 1
    corpo = client.get("/congresso/composicao?casa=camara").json()
    assert corpo["total"] == 513 == sum(i["n"] for i in corpo["hoje"])
    assert corpo["total_2027"] == 513 == sum(i["n"] for i in corpo["a_partir_2027"])
    assert corpo["hoje"][0] == {"partido": "PL", "n": 300}
    assert corpo["a_partir_2027"][0] == {"partido": "PL", "n": 250}
    assert corpo["fonte_2027_nome"]


def test_composicao_senado_soma_81_e_sem_eleitos_vem_nulo(client, session):
    ing = _ingestao(session)
    corpo = client.get("/congresso/composicao?casa=senado").json()
    assert corpo["a_partir_2027"] is None and corpo["hoje"] == []
    # 81 em exercício: 27 eleitos em 2022 (seguem) + 54 eleitos em 2018 (saem)
    seguem = []
    for i in range(27):
        p = _parl(session, ing, "senado", i, "PL" if i < 15 else "PT", uf="SP")
        seguem.append(p)
        _cand(
            session,
            ing,
            "SENADOR",
            "XX",
            i,
            ano=ANO - 4,
            uf="SP",
            situacao="ELEITO",
            parlamentar_id=p.id,
        )
    for i in range(27, 81):
        _parl(session, ing, "senado", i, "MDB", uf="SP")
    for i in range(54):
        _cand(
            session,
            ing,
            "SENADOR",
            "PSD" if i < 30 else "NOVO",
            100 + i,
            uf="SP",
            situacao="ELEITO",
        )
    corpo = client.get("/congresso/composicao?casa=senado").json()
    assert corpo["total"] == 81
    assert corpo["total_2027"] == 81
    por = {i["partido"]: i["n"] for i in corpo["a_partir_2027"]}
    # os que seguem aparecem com o partido de hoje (PL/PT), não o da candidatura (XX)
    assert por == {"PSD": 30, "NOVO": 24, "PL": 15, "PT": 12}
    assert client.get("/congresso/composicao?casa=outra").status_code == 422


def test_cadeiras_por_partido_junta_casas_e_eleicao_municipal(client, session):
    from decimal import Decimal

    from app.models import PartidoContaSoma

    ing = _ingestao(session)
    for i, p in enumerate(["PL", "PCdoB", "PL"]):
        _parl(session, ing, "camara", i, p)
    _parl(session, ing, "senado", 1, "MDB")
    _cand(session, ing, "PREFEITO", "PC do B", 1, ano=2024, situacao="ELEITO")
    _cand(session, ing, "VEREADOR", "PC do B", 2, ano=2024)
    _cand(session, ing, "VEREADOR", "PL", 3, ano=2024)
    _cand(session, ing, "VEREADOR", "NOVO", 4, ano=2024, situacao="NÃO ELEITO")
    session.add(
        PartidoContaSoma(
            ano=2024, tipo="receita", partido="PC do B", esfera="Nacional", uf="",
            fonte_recurso="x", natureza="x", categoria="x", valor=Decimal(1), lancamentos=1,
        )
    )  # fmt: skip
    session.flush()
    corpo = client.get("/partidos/cadeiras").json()
    por = {i["partido"]: i for i in corpo["itens"]}
    assert [i["partido"] for i in corpo["itens"]] == ["PL", "PCdoB", "MDB"]
    assert (por["PL"]["camara"], por["PL"]["vereadores"]) == (2, 1)
    assert (por["PCdoB"]["prefeitos"], por["PCdoB"]["vereadores"]) == (1, 1)
    assert por["PCdoB"]["sigla_contas"] == "PC do B"
    assert por["MDB"]["senado"] == 1 and "NOVO" not in por
    assert corpo["ano_municipal"] == 2024 and corpo["total_camara"] == 3
