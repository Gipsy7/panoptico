# ruff: noqa: E501  (recortes de respostas reais do SAPL)
from datetime import date

from app.models import Candidatura, Municipio
from ingestion.camaras import sapl
from tests.test_api import _ingestao


def test_ler_autoria_tipo_numero_e_ano():
    assert sapl.ler_autoria("Autoria: Adriana - Requerimento nº 324 de 2026") == (
        "Requerimento",
        324,
        2026,
    )
    assert sapl.ler_autoria("Autoria: X - Projeto de Lei Ordinária n° 62 de 2021") == (
        "Projeto de Lei Ordinária",
        62,
        2021,
    )
    assert sapl.ler_autoria("sem padrão") is None


def test_legislatura_atual_mandato_e_https():
    legislaturas = [
        {"id": 1, "data_inicio": "2021-01-01", "data_fim": "2024-12-31"},
        {"id": 2, "data_inicio": "2025-01-01", "data_fim": "2028-12-31"},
    ]
    assert sapl.legislatura_atual(legislaturas, date(2026, 10, 8))["id"] == 2
    assert sapl.em_exercicio(
        {"data_inicio_mandato": "2025-01-01", "data_fim_mandato": "2028-12-31"}, date(2026, 1, 1)
    )
    assert not sapl.em_exercicio(
        {"data_inicio_mandato": "2025-01-01", "data_fim_mandato": "2025-06-30"}, date(2026, 1, 1)
    )
    assert sapl._https("http://sapl.x.leg.br/foto.jpg") == "https://sapl.x.leg.br/foto.jpg"


def test_gravar_liga_ao_eleito_e_expoe_na_api(client, session):
    session.add(Municipio(ibge="4300034", nome="Aceguá", uf="RS", nome_chave="ACEGUA"))
    session.flush()
    session.add(Candidatura(ano_eleicao=2024, sq_candidato="1", cargo="VEREADOR", uf="RS", unidade="Aceguá",
                            municipio_ibge="4300034", nome="Adriana Machado Teixeira", nome_urna="Adriana",
                            situacao_turno="ELEITO POR QP", ingestao_id=_ingestao(session).id))  # fmt: skip
    session.flush()
    camara = {
        "base": "https://sapl.acegua.rs.leg.br/",
        "vereadores": [
            {"id_externo": "13", "nome": "Adriana Machado Teixeira", "nome_completo": None, "partido": "PSDB",
             "foto_url": None, "email": "a@x", "telefone": None, "titular": True, "em_exercicio": True,
             "inicio": "2025-01-01", "fim": "2028-12-31", "proposicoes_por_tipo": {"Requerimento": 22},
             "projetos": [{"id_externo": "1670", "tipo": "Projeto de Lei", "numero": 1, "ano": 2025,
                           "ementa": "Cria", "data_apresentacao": "2025-08-12", "em_tramitacao": False,
                           "primeiro_autor": True, "url": "https://sapl.acegua.rs.leg.br/materia/1670"}]},
            {"id_externo": "99", "nome": "Suplente Novo", "nome_completo": None, "partido": "PT",
             "foto_url": None, "email": None, "telefone": None, "titular": False, "em_exercicio": True,
             "inicio": "2026-03-01", "fim": None, "proposicoes_por_tipo": {}, "projetos": []},
        ],
    }  # fmt: skip
    assert sapl.gravar(session, "4300034", camara) == 2
    session.flush()
    corpo = client.get("/municipios/4300034/camara").json()
    adriana = next(v for v in corpo["itens"] if v["nome"].startswith("Adriana"))
    assert adriana["candidatura_id"] is not None and adriana["projetos"] == 1
    assert next(v for v in corpo["itens"] if v["nome"] == "Suplente Novo")["titular"] is False
    detalhe = client.get(f"/vereadores/{adriana['id']}").json()
    assert detalhe["proposicoes_por_tipo"] == [{"tipo": "Requerimento", "total": 22}]
    assert client.get("/municipios/0000000/camara").status_code == 404


def test_tipo_de_autor_parlamentar_pelo_nome():
    # Na Assembleia de Roraima, o id 1 é "Bloco Parlamentar"; "Parlamentar" é o 2.
    tipos = [{"id": 1, "descricao": "Bloco Parlamentar"}, {"id": 2, "descricao": "Parlamentar"}]
    assert sapl.tipo_parlamentar(tipos) == 2
    assert sapl.tipo_parlamentar([]) == 1


def test_assembleia_liga_ao_deputado_estadual_da_ultima_eleicao(client, session):
    ingestao = _ingestao(session).id
    for ano, sq in ((2018, "1"), (2022, "2")):
        session.add(Candidatura(ano_eleicao=ano, sq_candidato=sq, cargo="DEPUTADO ESTADUAL", uf="RR", unidade="Roraima",
                                nome="Catarina Guerra", nome_urna="Catarina Guerra", situacao_turno="ELEITO POR QP",
                                ingestao_id=ingestao))  # fmt: skip
    session.flush()
    casa = {
        "base": "https://sapl.al.rr.leg.br/",
        "vereadores": [
            {"id_externo": "7", "nome": "Catarina Guerra", "nome_completo": None, "partido": "UNIÃO",
             "foto_url": None, "email": None, "telefone": None, "titular": True, "em_exercicio": True,
             "inicio": "2023-02-01", "fim": "2027-01-31", "proposicoes_por_tipo": {"Indicação": 37}, "projetos": []},
        ],
    }  # fmt: skip
    assert sapl.gravar(session, None, casa, uf="RR") == 1
    session.flush()
    corpo = client.get("/estados/rr/assembleia").json()
    assert corpo["fonte_nome"] == "Sistema legislativo da assembleia (SAPL)"
    item = corpo["itens"][0]
    assert session.get(Candidatura, item["candidatura_id"]).ano_eleicao == 2022
    # O perfil do TSE aponta para o perfil da casa, que tem a atividade.
    eleito = client.get(f"/eleitos/{item['candidatura_id']}").json()
    assert eleito["mandato_local"] == {"id": item["id"], "casa": "assembleia"}
    detalhe = client.get(f"/vereadores/{item['id']}").json()
    assert (
        detalhe["casa"] == "assembleia"
        and detalhe["uf"] == "RR"
        and detalhe["municipio_ibge"] is None
    )
    assert client.get("/estados/SP/assembleia").status_code == 404
