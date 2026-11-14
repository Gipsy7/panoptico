from datetime import UTC, date, datetime
from decimal import Decimal

from app.models import (
    Candidatura,
    EmendaPagamento,
    Municipio,
    Parlamentar,
    ResultadoCandidato,
)
from app.services import emendas_votos, resultados_eleicao

IBGE = "4205902"
HOJE = date(2026, 11, 14)
AGORA = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def _parlamentar(session, n, nome, em_exercicio=True, casa="camara"):
    p = Parlamentar(
        casa=casa,
        id_externo=str(n),
        nome_parlamentar=nome,
        partido="ABC",
        uf="SC",
        em_exercicio=em_exercicio,
        fonte_url="https://exemplo.test",
        atualizado_em=AGORA,
    )
    session.add(p)
    session.flush()
    return p


def _candidato(session, sq, nome_urna, votos, parlamentar=None, ano=2022, situacao="ELEITO POR QP"):
    session.add(
        ResultadoCandidato(
            ano=ano,
            turno=1,
            cargo="DEPUTADO FEDERAL",
            abrangencia="municipio",
            uf="SC",
            municipio_ibge=IBGE,
            sq_candidato=sq,
            nome_urna=nome_urna,
            partido="ABC",
            votos=votos,
            situacao=situacao,
        )
    )
    session.add(
        Candidatura(
            ano_eleicao=ano,
            sq_candidato=sq,
            cargo="DEPUTADO FEDERAL",
            uf="SC",
            unidade="SANTA CATARINA",
            nome=nome_urna,
            nome_urna=nome_urna,
            parlamentar_id=parlamentar.id if parlamentar else None,
        )
    )
    session.flush()


def _emenda(session, parlamentar, valor, tipo=None, ibge=IBGE):
    session.add(
        EmendaPagamento(
            emenda_codigo="202612340001",
            ano_emenda=2024,
            ano_mes=202405,
            autor_codigo="1234",
            autor_nome="X",
            parlamentar_id=parlamentar.id if parlamentar else None,
            tipo=tipo,
            favorecido="PREFEITURA",
            favorecido_codigo="00000000000191",
            natureza="Município",
            grupo="prefeitura",
            municipio_ibge=ibge,
            valor=Decimal(valor),
        )
    )
    session.flush()


def _cidade(session):
    session.add(Municipio(ibge=IBGE, nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    ana = _parlamentar(session, 1, "Ana")
    beto = _parlamentar(session, 2, "Beto")
    saiu = _parlamentar(session, 3, "Quem Saiu", em_exercicio=False)
    _candidato(session, "10", "ANA", 4753, ana)
    _candidato(session, "11", "QUEM SAIU", 4000, saiu)
    _candidato(session, "12", "NAO ELEITO", 3000, None, situacao="NÃO ELEITO")
    _candidato(session, "13", "BETO DA URNA", 2000, beto)
    return ana, beto, saiu


def test_lista_so_quem_esta_em_exercicio_com_a_posicao_geral_e_zero_para_quem_nao_enviou(session):
    ana, beto, saiu = _cidade(session)
    _emenda(session, ana, "1000.00")
    _emenda(session, ana, "250.50")
    _emenda(session, saiu, "9999.00")  # entra no total da cidade, não na lista
    _emenda(session, ana, "777.00", ibge="4202404")  # outra cidade
    _emenda(session, ana, "5000.00", tipo="bancada")  # não é individual
    r = emendas_votos.do_municipio(session, IBGE, HOJE)
    assert r is not None
    assert r["ano_eleicao"] == 2022 and r["municipio"]["nome"] == "Gaspar"
    assert r["itens"] == [
        {
            "posicao": 1,
            "parlamentar_id": ana.id,
            "nome": "Ana",
            "partido": "ABC",
            "uf": "SC",
            "votos": 4753,
            "emendas_pagas": 1250.5,
        },
        {
            "posicao": 4,
            "parlamentar_id": beto.id,
            "nome": "Beto",
            "partido": "ABC",
            "uf": "SC",
            "votos": 2000,
            "emendas_pagas": 0.0,
        },
    ]
    # Dois dos mais votados ficaram de fora: um saiu do cargo, o outro não se elegeu.
    assert r["fora_por_nao_estar_em_exercicio"] == 2
    assert r["emendas_dos_listados"] == 1250.5
    assert r["emendas_individuais_da_cidade"] == 11249.5
    assert r["recorte"] and r["emendas_fonte_nome"] and r["votos_fonte_nome"]


def test_usa_a_eleicao_cujos_eleitos_ja_tomaram_posse(session):
    ana, beto, _ = _cidade(session)
    nova = _parlamentar(session, 9, "Nova")
    _candidato(session, "90", "NOVA", 9000, nova, ano=2026)
    # Em novembro de 2026 a legislatura em curso ainda é a eleita em 2022.
    assert emendas_votos.do_municipio(session, IBGE, date(2026, 11, 14))["ano_eleicao"] == 2022
    assert emendas_votos.do_municipio(session, IBGE, date(2027, 1, 31))["ano_eleicao"] == 2022
    # Na posse (1º/2/2027) passa a valer a de 2026.
    r = emendas_votos.do_municipio(session, IBGE, date(2027, 2, 1))
    assert r["ano_eleicao"] == 2026 and [i["nome"] for i in r["itens"]] == ["Nova"]


def test_limite_e_cidade_sem_dado(session):
    _cidade(session)
    assert len(emendas_votos.do_municipio(session, IBGE, HOJE, limite=1)["itens"]) == 1
    assert emendas_votos.do_municipio(session, "4202404", HOJE) is None  # sem resultado aqui
    assert emendas_votos.do_municipio(session, "9999999", HOJE) is None  # cidade que não existe


def test_senador_e_suplente_fora_do_cargo_nao_entram(session):
    session.add(Municipio(ibge=IBGE, nome="Gaspar", uf="SC", nome_chave="GASPAR"))
    session.flush()
    senador = _parlamentar(session, 5, "Hoje Senador", casa="senado")
    _candidato(session, "50", "HOJE SENADOR", 5000, senador)
    assert emendas_votos.do_municipio(session, IBGE, HOJE) is None


def test_mais_votados_traz_o_perfil_so_de_quem_esta_em_exercicio(session):
    ana, beto, saiu = _cidade(session)
    r = resultados_eleicao.mais_votados(session, IBGE, 2022)
    itens = {i["nome_urna"]: i["parlamentar_id"] for i in r["cargos"][0]["itens"]}
    assert itens == {"ANA": ana.id, "QUEM SAIU": None, "NAO ELEITO": None, "BETO DA URNA": beto.id}


def test_rotas(session, client):
    _cidade(session)
    r = client.get(f"/municipios/{IBGE}/emendas-dos-mais-votados")
    assert r.status_code == 200 and r.json()["itens"][0]["nome"] == "Ana"
    assert client.get("/municipios/9999999/emendas-dos-mais-votados").status_code == 404
    mv = client.get(f"/municipios/{IBGE}/mais-votados?ano=2022").json()
    assert mv["cargos"][0]["itens"][0]["parlamentar_id"] is not None
