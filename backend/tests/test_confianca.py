from datetime import UTC, date, datetime

from app.models import (
    Candidatura,
    Discurso,
    FonteIngestao,
    Municipio,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
)
from ingestion.comum import chave_nome
from tests.test_api import _ingestao, _popular


def _pessoa(session, nome):
    p = Pessoa(nome=nome, chave_nome=chave_nome(nome))
    session.add(p)
    session.flush()
    return p


def _vincular(session, pessoa, fonte, id_externo, regra="cpf"):
    session.add(PessoaVinculo(pessoa_id=pessoa.id, fonte=fonte, id_externo=id_externo, regra=regra))
    session.flush()


def _candidatura(session, ingestao, nome, cargo, uf, unidade, sq, ano=2024):
    c = Candidatura(
        ano_eleicao=ano,
        sq_candidato=sq,
        cargo=cargo,
        uf=uf,
        unidade=unidade,
        nome=nome,
        nome_urna=nome,
        situacao_turno="ELEITO",
        ingestao_id=ingestao,
    )
    session.add(c)
    session.flush()
    return c


def _carga(session, fonte, quando):
    session.add(
        FonteIngestao(
            fonte=fonte,
            url="x",
            arquivo_raw="x",
            status="ok",
            iniciado_em=quando,
            concluido_em=quando,
        )
    )
    session.flush()


def test_parlamentar_com_data_ultimo_registro_e_homonimo(client, session):
    _popular(session)
    ingestao = _ingestao(session).id
    deputado = session.query(Parlamentar).filter_by(casa="camara").first()
    _carga(session, "camara_deputados", datetime(2026, 11, 2, 15, 0, tzinfo=UTC))
    session.add(
        Discurso(
            casa="camara",
            id_externo="d1",
            parlamentar_id=deputado.id,
            data=date(2026, 10, 20),
        )
    )
    # O próprio, ligado à pessoa, e um homônimo vereador em outra cidade.
    eu = _pessoa(session, deputado.nome_civil or deputado.nome_parlamentar)
    _vincular(session, eu, "parlamentar", f"camara:{deputado.id_externo}")
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    outro = _pessoa(session, deputado.nome_civil or deputado.nome_parlamentar)
    c = _candidatura(session, ingestao, outro.nome, "VEREADOR", "SC", "Blumenau", "77")
    _vincular(session, outro, "candidatura", "2024:77", regra="tse")
    # Nome diferente: não entra.
    longe = _pessoa(session, "Fulano de Tal Completamente Diverso")
    _candidatura(session, ingestao, longe.nome, "VEREADOR", "SC", "Blumenau", "78")
    _vincular(session, longe, "candidatura", "2024:78", regra="tse")
    # Vínculo não publicável: não entra.
    oculto = _pessoa(session, outro.nome)
    _candidatura(session, ingestao, oculto.nome, "VEREADOR", "SC", "Blumenau", "79")
    _vincular(session, oculto, "candidatura", "2024:79", regra="nome_casa")

    corpo = client.get(f"/pessoas/de/confianca?tipo=parlamentar&id={deputado.id}").json()
    assert corpo["conferido_em"] == "2026-11-02"
    assert corpo["fonte"] == "Dados Abertos da Câmara dos Deputados"
    assert corpo["ultimo_registro"] == {"tipo": "discurso em plenário", "data": "2026-10-20"}
    assert corpo["parecidos"] == [
        {
            "nome": outro.nome,
            "cargo": "Vereador",
            "lugar": "Blumenau/SC",
            "href": f"/eleito/{c.id}",
        }
    ]


def test_sem_pessoa_sem_registro_e_sem_parecidos(client, session):
    _popular(session)
    deputado = session.query(Parlamentar).filter_by(casa="senado").first()
    corpo = client.get(f"/pessoas/de/confianca?tipo=parlamentar&id={deputado.id}").json()
    assert corpo["conferido_em"] is None
    assert corpo["fonte"] == "Dados Abertos do Senado Federal"
    assert corpo["ultimo_registro"] is None
    assert corpo["parecidos"] == []


def test_mesmo_cargo_e_lugar_nao_vira_parecido_e_perfil_inexistente(client, session):
    ingestao = _ingestao(session).id
    a = _pessoa(session, "Maria Aparecida Souza")
    ca = _candidatura(session, ingestao, a.nome, "VEREADOR", "SC", "Blumenau", "1")
    _vincular(session, a, "candidatura", "2024:1", regra="tse")
    b = _pessoa(session, "Maria Aparecida Souza")
    _candidatura(session, ingestao, b.nome, "VEREADOR", "SC", "Blumenau", "2")
    _vincular(session, b, "candidatura", "2024:2", regra="tse")
    corpo = client.get(f"/pessoas/de/confianca?tipo=candidatura&id={ca.id}").json()
    assert corpo["parecidos"] == []
    assert corpo["fonte"].startswith("Dados Abertos do TSE")
    assert client.get("/pessoas/de/confianca?tipo=candidatura&id=999999").status_code == 404
