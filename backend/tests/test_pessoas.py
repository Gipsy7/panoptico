from datetime import date

from sqlalchemy import select

from app.models import Candidatura, MandatoLocal, Parlamentar, Pessoa, PessoaVinculo
from ingestion import pessoas as carga
from ingestion.identidade import Aresta, agrupar


def _regras(pessoas):
    return sorted(sorted((c[1], regra) for c, regra in membros) for membros in pessoas)


def test_agrupar_por_chave_forte_e_recusa_cpf_diferente():
    cpfs = {("c", "a"): "111", ("c", "b"): None, ("c", "x"): "222", ("p", "1"): "111"}
    arestas = [
        Aresta(("c", "a"), ("c", "b"), "titulo"),
        Aresta(("p", "1"), ("c", "a"), "cpf"),
        # Título repetido entre CPFs diferentes: não funde as duas pessoas.
        Aresta(("c", "b"), ("c", "x"), "titulo"),
    ]
    pessoas, recusadas = agrupar(cpfs, arestas)
    assert len(pessoas) == 2 and len(recusadas) == 1
    assert sorted(len(p) for p in pessoas) == [1, 3]


def test_ligacao_por_nome_marca_o_bloco_inteiro_como_media():
    # Bloco forte A (duas candidaturas pelo título) e bloco B (mandato + outro registro
    # ligados por CPF), unidos só pelo nome: todo o bloco menor fica com a regra média.
    cpfs = {("c", "1"): None, ("c", "2"): None, ("c", "3"): None, ("m", "1"): "9", ("x", "1"): "9"}
    arestas = [
        Aresta(("c", "1"), ("c", "2"), "titulo"),
        Aresta(("c", "2"), ("c", "3"), "titulo"),
        Aresta(("m", "1"), ("x", "1"), "cpf"),
        Aresta(("c", "1"), ("m", "1"), "nome_casa"),
    ]
    pessoas, _ = agrupar(cpfs, arestas)
    assert len(pessoas) == 1
    regras = dict((c, r) for c, r in pessoas[0])
    assert regras[("m", "1")] == regras[("x", "1")] == "nome_casa"
    assert {regras[("c", "1")], regras[("c", "2")], regras[("c", "3")]} == {"origem", "titulo"}


def _candidatura(session, ano, sq, titulo, **extra):
    c = Candidatura(
        ano_eleicao=ano, sq_candidato=sq, cargo=extra.pop("cargo", "DEPUTADO ESTADUAL"),
        uf="AC", unidade="Acre", nome=extra.pop("nome", "Ana Maria Souza"), nome_urna="Ana",
        titulo=titulo, situacao_turno=extra.pop("situacao_turno", "ELEITO POR QP"),
        genero="FEMININO", partido="PT", **extra,
    )  # fmt: skip
    session.add(c)
    session.flush()
    return c


def _cenario(session):
    parlamentar = Parlamentar(
        casa="camara", id_externo="999", nome_parlamentar="Ana Souza", nome_civil="Ana Maria Souza",
        uf="AC", cpf="12345678901", fonte_url="https://x", atualizado_em=date(2026, 1, 1),
    )  # fmt: skip
    session.add(parlamentar)
    session.flush()
    c2022 = _candidatura(session, 2022, "1", "000111", cpf="12345678901",
                         parlamentar_id=parlamentar.id, cargo="DEPUTADO FEDERAL")  # fmt: skip
    c2018 = _candidatura(session, 2018, "2", "000111", cpf="12345678901",
                         data_nascimento=date(1980, 5, 1))  # fmt: skip
    c2024 = _candidatura(session, 2024, "3", "000222", nome="Rui Lima", cargo="VEREADOR",
                         situacao_turno="ELEITO POR MÉDIA")  # fmt: skip
    mandato = MandatoLocal(
        casa="assembleia", uf="AC", id_externo="77", nome="Dra. Ana Souza", candidatura_id=c2018.id,
        sapl_url="https://sapl.al.ac.leg.br/",
    )  # fmt: skip
    session.add(mandato)
    session.flush()
    return parlamentar, c2022, c2018, c2024, mandato


def _pessoa_de(session, fonte, id_externo):
    return session.scalar(
        select(PessoaVinculo.pessoa_id).where(
            PessoaVinculo.fonte == fonte, PessoaVinculo.id_externo == id_externo
        )
    )


def test_carga_liga_e_mantem_ids(session):
    _cenario(session)
    _, pessoas, recusadas, mudaram = carga.processar(session)
    assert (len(pessoas), recusadas, mudaram) == (2, [], 2)
    ana = _pessoa_de(session, "parlamentar", "camara:999")
    assert _pessoa_de(session, "candidatura", "2018:2") == ana
    assert _pessoa_de(session, "mandato_local", "assembleia:AC::77") == ana
    assert _pessoa_de(session, "candidatura", "2024:3") != ana
    registro = session.get(Pessoa, ana)
    assert (registro.nome, registro.data_nascimento) == ("Ana Maria Souza", date(1980, 5, 1))
    # Recarga sem mudança: mesmos ids e nada regravado.
    _, _, _, mudaram = carga.processar(session)
    assert mudaram == 0 and _pessoa_de(session, "parlamentar", "camara:999") == ana


def test_titulo_novo_funde_duas_pessoas_na_de_menor_id(session):
    _, _, _, c2024, _ = _cenario(session)
    carga.processar(session)
    ana = _pessoa_de(session, "parlamentar", "camara:999")
    rui = _pessoa_de(session, "candidatura", "2024:3")
    c2024.titulo = "000111"  # descobre-se que é a mesma pessoa
    session.flush()
    carga.processar(session)
    assert _pessoa_de(session, "candidatura", "2024:3") == min(ana, rui)
    assert session.get(Pessoa, max(ana, rui)) is None


def test_api_publica_so_vinculo_forte_e_monta_a_linha_do_tempo(client, session):
    _, _, _, _, mandato = _cenario(session)
    carga.processar(session)
    ana = _pessoa_de(session, "parlamentar", "camara:999")
    corpo = client.get(f"/pessoas/{ana}").json()
    tipos = [p["tipo"] for p in corpo["perfis"]]
    # O mandato na assembleia foi ligado pelo nome: só aparece depois de revisado.
    assert "deputado_estadual" not in tipos and tipos.count("candidatura") == 2
    session.execute(
        PessoaVinculo.__table__.update()
        .where(PessoaVinculo.fonte == "mandato_local")
        .values(revisado=True)
    )
    corpo = client.get(f"/pessoas/{ana}").json()
    assert {
        "tipo": "deputado_estadual",
        "id": mandato.id,
        "descricao": "Mandato atual na casa",
    } in corpo["perfis"]

    linha = client.get(f"/pessoas/{ana}/eventos").json()["itens"]
    assert [i["descricao"] for i in linha] == [
        "Eleita para deputada federal em Acre (AC) nas eleições de 2022, pelo PT",
        "Eleita para deputada estadual em Acre (AC) nas eleições de 2018, pelo PT",
    ]
    assert linha[0]["data"] == "2022-10-02"  # turno único: data do 1º turno
    assert (
        client.get(f"/pessoas/{ana}/eventos", params={"de": "2020-01-01"}).json()["itens"][0][
            "data"
        ]
        == "2022-10-02"
    )
    assert client.get("/pessoas/999999").status_code == 404


def test_nome_identico_na_casa_e_forte_e_revisao_aceita_publica(
    client, session, tmp_path, monkeypatch
):
    _, _, c2018, _, mandato = _cenario(session)
    carga.processar(session)
    regra = session.scalar(
        select(PessoaVinculo.regra).where(PessoaVinculo.fonte == "mandato_local")
    )
    assert regra == "nome_casa"  # "Dra. Ana Souza" x "Ana" / "Ana Maria Souza": aproximado
    # Revisão humana aceita: passa a ser publicado.
    revisoes = tmp_path / "vinculos_revisados.csv"
    revisoes.write_text(
        "fonte,id_externo,ligado_a,decisao,revisado_por,revisado_em,observacao\n"
        "mandato_local,assembleia:AC::77,candidatura:2018:2,aceito,Fulano,2026-10-09,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(carga, "REVISOES", revisoes)
    carga.processar(session)
    assert (
        session.scalar(select(PessoaVinculo.revisado).where(PessoaVinculo.fonte == "mandato_local"))
        is True
    )
    # Nome idêntico ao de urna: forte, sem revisão.
    mandato.nome = "Ana"
    session.flush()
    revisoes.write_text(
        "fonte,id_externo,ligado_a,decisao,revisado_por,revisado_em,observacao\n", encoding="utf-8"
    )
    carga.processar(session)
    assert (
        session.scalar(select(PessoaVinculo.regra).where(PessoaVinculo.fonte == "mandato_local"))
        == "nome_exato_casa"
    )


def test_revisao_recusada_desfaz_a_ligacao(session, tmp_path, monkeypatch):
    _cenario(session)
    revisoes = tmp_path / "vinculos_revisados.csv"
    revisoes.write_text(
        "fonte,id_externo,ligado_a,decisao,revisado_por,revisado_em,observacao\n"
        "mandato_local,assembleia:AC::77,candidatura:2018:2,recusado,Fulano,2026-10-09,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(carga, "REVISOES", revisoes)
    carga.processar(session)
    assert _pessoa_de(session, "mandato_local", "assembleia:AC::77") != _pessoa_de(
        session, "candidatura", "2018:2"
    )
