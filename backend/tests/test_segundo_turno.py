from datetime import date
from decimal import Decimal

import respx

from app.models import (
    BemDeclarado,
    CampanhaResumo,
    Candidatura,
    Evento,
    Pessoa,
    PessoaVinculo,
)
from app.services import segundo_turno
from tests.test_api import _ingestao

ANO = date.today().year  # a página só mostra a eleição do ano corrente
DATA_2T = segundo_turno.data_segundo_turno(ANO)


def _cand(session, ingestao, nome, cargo, situacao, numero, ano=ANO, uf="SC", **campos):
    c = Candidatura(
        ano_eleicao=ano,
        sq_candidato=f"{nome}-{ano}-{cargo}"[:20],
        cargo=cargo,
        uf=uf,
        unidade="Santa Catarina" if uf == "SC" else "Brasil",
        nome=nome,
        nome_urna=nome,
        partido="PX",
        numero=numero,
        situacao_turno=situacao,
        ingestao_id=ingestao,
        **campos,
    )
    session.add(c)
    session.flush()
    return c


def _ligar(session, pessoa, candidatura, regra="titulo"):
    v = PessoaVinculo(
        pessoa_id=pessoa.id,
        fonte="candidatura",
        id_externo=f"{candidatura.ano_eleicao}:{candidatura.sq_candidato}",
        regra=regra,
    )
    session.add(v)
    session.flush()
    return v


def _cenario(session):
    ing = _ingestao(session).id
    # Mais votado tem número maior: a ordem tem de ser pelo número, não pelos votos.
    a = _cand(session, ing, "Gov Quarenta", "GOVERNADOR", "2º TURNO", "45", votos=900)
    b = _cand(session, ing, "Gov Treze", "GOVERNADOR", "2º TURNO", "13", votos=500)
    _cand(session, ing, "Vice Treze", "VICE-GOVERNADOR", "2º TURNO", "13", chapa_titular_id=b.id)
    _cand(session, ing, "Gov Fora", "GOVERNADOR", "NÃO ELEITO", "50", votos=100)
    _cand(session, ing, "Gov Outro", "GOVERNADOR", "2º TURNO", "22", uf="RS")
    _cand(session, ing, "Pres Um", "PRESIDENTE", "2º TURNO", "22", uf="BR", votos=10)
    session.add_all(
        [
            BemDeclarado(candidatura_id=b.id, ordem=1, tipo="Casa", descricao="x", valor=300),
            BemDeclarado(candidatura_id=b.id, ordem=2, tipo="Carro", descricao="y", valor=50),
            CampanhaResumo(
                candidatura_id=b.id,
                receitas_total=Decimal(1000),
                receitas_por_origem={"Recursos de pessoas físicas": 200, "Fundo Especial": 800},
                despesas_total=Decimal(700),
                despesas_por_tipo={"Publicidade": 700},
                numero_doadores=3,
            ),
        ]
    )
    # Treze foi deputado em 2022 (com bens) e tem um registro na CGU.
    pessoa = Pessoa(nome="Gov Treze", chave_nome="GOV TREZE")
    session.add(pessoa)
    session.flush()
    _ligar(session, pessoa, b)
    antiga = _cand(session, ing, "Gov Treze", "DEPUTADO FEDERAL", "ELEITO POR QP", "1313", ano=2022)
    session.add(
        BemDeclarado(candidatura_id=antiga.id, ordem=1, tipo="Casa", descricao="x", valor=200)
    )
    vinculo = _ligar(session, pessoa, antiga)
    session.add(
        Evento(
            pessoa_id=pessoa.id,
            vinculo_id=vinculo.id,
            data=date(2020, 1, 2),
            tipo="sancao",
            descricao="Multa",
            orgao="Órgão X",
            fonte="cgu_sancoes",
            id_externo="s1",
        )
    )
    # Quarenta tem pessoa ligada, mas sem histórico nem registros.
    outra = Pessoa(nome="Gov Quarenta", chave_nome="GOV QUARENTA")
    session.add(outra)
    session.flush()
    _ligar(session, outra, a)
    session.flush()
    return a, b


def test_data_do_segundo_turno_e_ultimo_domingo_de_outubro():
    assert segundo_turno.data_segundo_turno(2026) == date(2026, 10, 25)
    assert segundo_turno.data_segundo_turno(2022) == date(2022, 10, 30)
    assert segundo_turno.data_segundo_turno(2018) == date(2018, 10, 28)
    assert segundo_turno._em_andamento(2026, date(2026, 10, 25))
    assert not segundo_turno._em_andamento(2026, date(2026, 10, 26))
    assert not segundo_turno._em_andamento(None)


def test_comparador_mesmos_campos_e_ordem_pelo_numero(client, session):
    a, b = _cenario(session)
    corpo = client.get("/segundo-turno?uf=sc").json()
    assert corpo["localizacao"]["uf"] == "SC"
    assert corpo["ano_eleicao"] == ANO
    assert corpo["data_segundo_turno"] == DATA_2T.isoformat()
    presidente, governador = corpo["disputas"]
    assert (presidente["chave"], presidente["faltam"]) == ("presidente", 1)
    assert governador["unidade"] == "Santa Catarina" and governador["faltam"] == 0
    assert [c["numero"] for c in governador["candidatos"]] == ["13", "45"]
    # Os dois têm exatamente os mesmos campos.
    treze, quarenta = governador["candidatos"]
    assert treze.keys() == quarenta.keys()
    assert treze["vice"]["nome_urna"] == "Vice Treze" and quarenta["vice"] is None
    assert treze["votos_1turno"] == 500
    assert treze["bens"]["total"] == 350 and treze["bens"]["quantidade"] == 2
    assert treze["bens"]["anterior"] == {"ano": 2022, "cargo": "Deputado federal", "total": 200}
    assert treze["campanha"]["receitas_total"] == 1000
    # Origem agregada, maior primeiro; nenhum nome de doador.
    assert [o["nome"] for o in treze["campanha"]["receitas_por_origem"]] == [
        "Fundo Especial",
        "Recursos de pessoas físicas",
    ]
    assert [(c["ano"], c["eleito"]) for c in treze["carreira"]] == [(2022, True)]
    assert treze["sancoes"][0]["orgao"] == "Órgão X"
    assert treze["perfil"] == f"/eleito/{b.id}"
    # Sem dado: nulo (o site diz "não informado"); pessoa ligada sem registros: lista vazia.
    assert quarenta["bens"] is None and quarenta["campanha"] is None
    assert quarenta["carreira"] == [] and quarenta["sancoes"] == []
    assert corpo["governador_eleito_1turno"] is None


def test_estado_sem_segundo_turno_para_governador(client, session):
    _cenario(session)
    _cand(session, _ingestao(session).id, "Gov Eleito", "GOVERNADOR", "ELEITO", "40", uf="PR")
    corpo = client.get("/segundo-turno?uf=PR").json()
    assert [d["chave"] for d in corpo["disputas"]] == ["presidente"]
    assert corpo["governador_eleito_1turno"]["nome_urna"] == "Gov Eleito"
    # Candidato sem pessoa ligada: carreira e registros nulos (não "nenhum").
    pres = corpo["disputas"][0]["candidatos"][0]
    assert pres["carreira"] is None and pres["sancoes"] is None


def test_agenda(client, session):
    vazio = client.get("/segundo-turno/agenda").json()
    assert vazio["em_andamento"] is False and vazio["ufs_governador"] == []
    _cenario(session)
    corpo = client.get("/segundo-turno/agenda").json()
    assert corpo["presidente"] is True
    assert corpo["ufs_governador"] == ["RS", "SC"]
    assert corpo["data_segundo_turno"] == DATA_2T.isoformat()


@respx.mock
def test_por_cep_e_erros(client, session):
    _cenario(session)
    respx.get("https://viacep.com.br/ws/88010000/json/").respond(
        json={"localidade": "Florianópolis", "uf": "SC", "ibge": "4205407"}
    )
    corpo = client.get("/segundo-turno?cep=88010-000").json()
    assert corpo["localizacao"]["municipio"] == "Florianópolis"
    assert len(corpo["disputas"]) == 2
    assert client.get("/segundo-turno").status_code == 422
    assert client.get("/segundo-turno?uf=XX").status_code == 422


def test_depois_do_resultado(client, session):
    ing = _ingestao(session).id
    primeiro = date(ANO, 10, 4)
    eleito = _cand(session, ing, "Vence", "GOVERNADOR", "ELEITO", "45", votos=700,
                   data_eleicao=DATA_2T)  # fmt: skip
    _cand(session, ing, "Perde", "GOVERNADOR", "NÃO ELEITO", "13", votos=600, data_eleicao=DATA_2T)
    # Quem perdeu no 1º turno não entra; nem o governador eleito no 1º turno de outro estado.
    _cand(session, ing, "Fora", "GOVERNADOR", "NÃO ELEITO", "50", votos=10, data_eleicao=primeiro)
    _cand(session, ing, "Direto", "GOVERNADOR", "ELEITO", "40", uf="PR", data_eleicao=primeiro)
    _cand(session, ing, "Vice Vence", "VICE-GOVERNADOR", "ELEITO", "45", chapa_titular_id=eleito.id)
    corpo = client.get("/segundo-turno?uf=SC").json()
    (disputa,) = corpo["disputas"]
    assert disputa["decidida"] is True
    assert [(c["nome_urna"], c["eleito"]) for c in disputa["candidatos"]] == [
        ("Perde", False),
        ("Vence", True),
    ]
    vence = disputa["candidatos"][1]
    # Depois do resultado, a coluna de votos é a do 2º turno: nunca rotulada como 1º.
    assert (vence["votos_1turno"], vence["votos_2turno"]) == (None, 700)
    assert vence["vice"]["nome_urna"] == "Vice Vence"
    pr = client.get("/segundo-turno?uf=PR").json()
    assert pr["disputas"] == [] and pr["governador_eleito_1turno"]["nome_urna"] == "Direto"
    # No ano seguinte, a eleição passada não aparece como 2º turno.
    assert segundo_turno._ano(session, date(ANO + 1, 1, 10)) is None


def test_antes_do_resultado_votos_sao_do_1_turno(client, session):
    _cenario(session)
    governador = client.get("/segundo-turno?uf=SC").json()["disputas"][1]
    assert governador["decidida"] is False
    assert {(c["votos_2turno"], c["eleito"]) for c in governador["candidatos"]} == {(None, None)}
