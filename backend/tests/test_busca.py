# ruff: noqa: E501  (dados montados numa linha só)
from app.models import Candidatura, MandatoLocal, Municipio, Pessoa, PessoaVinculo
from ingestion.comum import chave_nome
from tests.test_api import _ingestao, _popular


def _candidatura(session, ingestao, **campos):
    base = {
        "sq_candidato": campos["nome"],
        "uf": "SC",
        "situacao_turno": "ELEITO",
        "ingestao_id": ingestao,
    }
    session.add(Candidatura(**{**base, **campos}))


def test_busca_em_todos_os_niveis_sem_acento_e_sem_repetir(client, session):
    _popular(session)
    ingestao = _ingestao(session).id
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    _candidatura(
        session,
        ingestao,
        ano_eleicao=2024,
        cargo="VEREADOR",
        unidade="Blumenau",
        municipio_ibge="4202404",
        nome="José Antônio Peçanha",
        nome_urna="Zé Peçanha",
    )
    _candidatura(
        session,
        ingestao,
        ano_eleicao=2024,
        cargo="PREFEITO",
        unidade="Blumenau",
        municipio_ibge="4202404",
        nome="Maria Peçanha",
        nome_urna="Maria Peçanha",
    )
    # Eleição antiga do mesmo cargo: não aparece.
    _candidatura(
        session,
        ingestao,
        ano_eleicao=2018,
        cargo="GOVERNADOR",
        unidade="SC",
        nome="Velho Pecanha",
        nome_urna="Velho Pecanha",
    )
    _candidatura(
        session,
        ingestao,
        ano_eleicao=2022,
        cargo="GOVERNADOR",
        unidade="SC",
        nome="Outro Nome",
        nome_urna="Outro Nome",
    )
    session.flush()
    ze = session.query(Candidatura).filter_by(nome_urna="Zé Peçanha").one()
    session.add(MandatoLocal(casa="camara", uf="SC", municipio_ibge="4202404", id_externo="1",
                             nome="Zé Peçanha", partido="PT", candidatura_id=ze.id,
                             proposicoes_por_tipo={}, sapl_url="https://sapl.x/"))  # fmt: skip
    session.flush()

    itens = client.get("/busca", params={"nome": "pecanha"}).json()["itens"]
    assert [(i["nome"], i["cargo"]) for i in itens] == [
        ("Maria Peçanha", "Prefeito"),
        ("Zé Peçanha", "Vereador"),
    ]
    vereador = itens[1]
    assert vereador["caminho"].startswith("/vereador/") and vereador["lugar"] == "Blumenau/SC"
    assert itens[0]["nome_completo"] is None  # igual ao nome de urna
    # Pelo nome civil, mostrando o nome completo.
    assert (
        client.get("/busca", params={"nome": "jose antonio"}).json()["itens"][0]["nome_completo"]
        == "José Antônio Peçanha"
    )
    assert client.get("/busca", params={"nome": "ab"}).json()["itens"] == []


def _pessoa_com_candidatura(session, ingestao, nome, ano, regra, revisado=False, cargo="VEREADOR"):
    """Vereadora eleita numa eleição antiga (fora do mandato em curso), ligada a uma pessoa."""
    _candidatura(
        session, ingestao, ano_eleicao=ano, cargo=cargo, unidade="Joinville", nome=nome,
        nome_urna=nome, municipio_ibge="4209102", partido="PSD",
    )  # fmt: skip
    session.flush()
    c = session.query(Candidatura).filter_by(nome=nome).one()
    pessoa = Pessoa(nome=nome, chave_nome=chave_nome(nome))
    session.add(pessoa)
    session.flush()
    session.add(
        PessoaVinculo(
            pessoa_id=pessoa.id, fonte="candidatura", id_externo=f"{ano}:{nome}",
            regra=regra, revisado=revisado,
        )
    )  # fmt: skip
    session.flush()
    return c


def test_busca_partidos_por_sigla_e_nome(client):
    corpo = client.get("/busca", params={"q": "pt"}).json()
    assert corpo["itens"] == [] and corpo["pessoas"] == []  # 2 letras: só a sigla
    assert [(p["sigla"], p["caminho"]) for p in corpo["partidos"]] == [("PT", "/partidos/PT")]
    por_nome = client.get("/busca", params={"q": "trabalhista"}).json()["partidos"]
    assert {p["sigla"] for p in por_nome} >= {"PDT", "PTB", "PRTB"}
    assert len(client.get("/busca", params={"q": "partido"}).json()["partidos"]) == 5  # limite
    assert client.get("/busca", params={"q": "uniao"}).json()["partidos"][0]["sigla"] == "UNIÃO"
    assert client.get("/busca", params={"q": "pc do b"}).json()["partidos"][0]["caminho"] == (
        "/partidos/PC%20do%20B"
    )


def test_busca_aceita_q_e_nome_e_exige_um(client):
    assert client.get("/busca", params={"nome": "pt"}).status_code == 200
    assert client.get("/busca").status_code == 422


def test_busca_pessoa_so_com_vinculo_publicavel(client, session):
    ingestao = _ingestao(session).id
    # A eleição de 2020 é a do mandato em curso; a de 2016 já ficou para trás.
    _candidatura(session, ingestao, ano_eleicao=2020, cargo="VEREADOR", unidade="Joinville",
                 nome="Qualquer Um", nome_urna="Qualquer Um")  # fmt: skip
    _pessoa_com_candidatura(session, ingestao, "Zenaide Marquês", 2016, "origem")
    _pessoa_com_candidatura(session, ingestao, "Zenilda Marquês", 2016, "nome_casa")  # só por nome
    _pessoa_com_candidatura(session, ingestao, "Zenita Marquês", 2016, "nome_casa", revisado=True)
    corpo = client.get("/busca", params={"q": "marques"}).json()
    assert corpo["itens"] == []
    assert [p["nome"] for p in corpo["pessoas"]] == ["Zenaide Marquês", "Zenita Marquês"]
    primeira = corpo["pessoas"][0]
    assert primeira["cargo"] == "Vereador, eleição de 2016" and primeira["lugar"] == "Joinville/SC"
    assert primeira["caminho"].startswith("/eleito/")
    # Acento e nome parcial dão o mesmo resultado.
    assert client.get("/busca", params={"q": "MARQUÊS zena"}).json()["pessoas"][0]["nome"] == (
        "Zenaide Marquês"
    )


def test_busca_nao_repete_quem_ja_esta_nos_eleitos_e_limita_os_grupos(client, session):
    ingestao = _ingestao(session).id
    for i in range(25):
        _candidatura(
            session, ingestao, ano_eleicao=2024, cargo="VEREADOR", unidade="Joinville",
            nome=f"Torres {i:02d}", nome_urna=f"Torres {i:02d}", municipio_ibge="4209102",
        )  # fmt: skip
    session.flush()
    for c in session.query(Candidatura).filter(Candidatura.nome.like("Torres%")):
        pessoa = Pessoa(nome=c.nome, chave_nome=chave_nome(c.nome))
        session.add(pessoa)
        session.flush()
        session.add(
            PessoaVinculo(
                pessoa_id=pessoa.id, fonte="candidatura",
                id_externo=f"2024:{c.sq_candidato}", regra="origem",
            )
        )  # fmt: skip
    session.flush()
    corpo = client.get("/busca", params={"q": "torres"}).json()
    assert len(corpo["itens"]) == 20  # limite do grupo
    caminhos = {i["caminho"] for i in corpo["itens"]}
    # As 5 que não couberam em itens aparecem em pessoas; nenhuma aparece nos dois.
    assert len(corpo["pessoas"]) == 5
    assert not caminhos & {p["caminho"] for p in corpo["pessoas"]}


def test_busca_resposta_cacheavel_na_cdn(client):
    cabecalho = client.get("/busca", params={"q": "lira"}).headers["cache-control"]
    assert "s-maxage=3600" in cabecalho
