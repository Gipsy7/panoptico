# ruff: noqa: E501  (dados montados numa linha só)
from app.models import Candidatura, MandatoLocal, Municipio
from tests.test_api import _ingestao, _popular


def _candidatura(session, ingestao, **campos):
    base = {"sq_candidato": campos["nome"], "uf": "SC", "situacao_turno": "ELEITO", "ingestao_id": ingestao}
    session.add(Candidatura(**{**base, **campos}))


def test_busca_em_todos_os_niveis_sem_acento_e_sem_repetir(client, session):
    _popular(session)
    ingestao = _ingestao(session).id
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    _candidatura(session, ingestao, ano_eleicao=2024, cargo="VEREADOR", unidade="Blumenau",
                 municipio_ibge="4202404", nome="José Antônio Peçanha", nome_urna="Zé Peçanha")
    _candidatura(session, ingestao, ano_eleicao=2024, cargo="PREFEITO", unidade="Blumenau",
                 municipio_ibge="4202404", nome="Maria Peçanha", nome_urna="Maria Peçanha")
    # Eleição antiga do mesmo cargo: não aparece.
    _candidatura(session, ingestao, ano_eleicao=2018, cargo="GOVERNADOR", unidade="SC",
                 nome="Velho Pecanha", nome_urna="Velho Pecanha")
    _candidatura(session, ingestao, ano_eleicao=2022, cargo="GOVERNADOR", unidade="SC",
                 nome="Outro Nome", nome_urna="Outro Nome")
    session.flush()
    ze = session.query(Candidatura).filter_by(nome_urna="Zé Peçanha").one()
    session.add(MandatoLocal(casa="camara", uf="SC", municipio_ibge="4202404", id_externo="1",
                             nome="Zé Peçanha", partido="PT", candidatura_id=ze.id,
                             proposicoes_por_tipo={}, sapl_url="https://sapl.x/"))  # fmt: skip
    session.flush()

    itens = client.get("/busca", params={"nome": "pecanha"}).json()["itens"]
    assert [(i["nome"], i["cargo"]) for i in itens] == [("Maria Peçanha", "Prefeito"), ("Zé Peçanha", "Vereador")]
    vereador = itens[1]
    assert vereador["caminho"].startswith("/vereador/") and vereador["lugar"] == "Blumenau/SC"
    assert itens[0]["nome_completo"] is None  # igual ao nome de urna
    # Pelo nome civil, mostrando o nome completo.
    assert client.get("/busca", params={"nome": "jose antonio"}).json()["itens"][0]["nome_completo"] == "José Antônio Peçanha"
    assert client.get("/busca", params={"nome": "ab"}).json()["itens"] == []
