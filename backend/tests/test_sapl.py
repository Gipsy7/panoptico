# ruff: noqa: E501  (recortes de respostas reais do SAPL)
from datetime import date

from app.models import Candidatura, Municipio, VotacaoLocal
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
    # Casa que parou de atualizar o SAPL: nada de mostrar a legislatura antiga.
    assert sapl.legislatura_atual(legislaturas[:1], date(2026, 10, 8)) is None
    assert sapl.legislatura_atual(legislaturas[:1], date(2025, 2, 1))["id"] == 1  # transição
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
             "inicio": "2023-02-01", "fim": "2027-01-31", "proposicoes_por_tipo": {"Indicação": 37}, "projetos": [],
             "sessoes": 10, "presencas": 8},
            {"id_externo": "8", "nome": "Outro Deputado", "nome_completo": None, "partido": "PL",
             "foto_url": None, "email": None, "telefone": None, "titular": True, "em_exercicio": True,
             "inicio": "2023-02-01", "fim": "2027-01-31", "proposicoes_por_tipo": {}, "projetos": [],
             "sessoes": 10, "presencas": 6},
        ],
        "votacoes": [{"id_externo": "107", "materia": "Veto nº 1 de 2025", "resultado": "Aprovado", "sim": 15,
                      "nao": 0, "abstencoes": 0, "data": "2025-06-26", "materia_id": 17398}],
        "votos": [{"votacao": "107", "parlamentar": "7", "voto": "Sim"},
                  {"votacao": "107", "parlamentar": "8", "voto": "Não Votou"}],
    }  # fmt: skip
    assert sapl.gravar(session, None, casa, uf="RR") == 2
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
    # Presença: 8 de 10; média da casa = (80% + 60%) / 2 = 70%.
    assert detalhe["presenca"] == {"sessoes": 10, "presencas": 8, "media_casa": 70.0}
    assert detalhe["votacoes"] == 1
    votos = client.get(f"/vereadores/{item['id']}/votacoes").json()
    assert votos["casa_registra"] and votos["total"] == 1 and votos["votou"] == 1
    outro = corpo["itens"][1]
    assert outro["votacoes"] == 0  # "Não Votou" não conta como voto
    assert votos["itens"][0]["voto"] == "Sim"
    assert votos["itens"][0]["url"] == "https://sapl.al.rr.leg.br/materia/17398"
    # Regravar não duplica votações.
    sapl.gravar(session, None, casa, uf="RR")
    session.flush()
    assert session.query(VotacaoLocal).count() == 1
    assert client.get("/estados/SP/assembleia").status_code == 404


def test_ler_registro_de_votacao():
    texto = "Ordem: Ordem do Dia/Expediente: 1 - Requerimento nº 62 de 2025 em 33ª Ordinária da 3ª Sessão Legislativa da 16ª Legislatura - Votação: Aprovado"
    assert sapl.ler_registro(texto) == ("Requerimento nº 62 de 2025", "Aprovado")
    assert sapl.ler_registro("sem padrão") == ("sem padrão", None)


class _SaplFalso:
    """Respostas recortadas da Assembleia do Acre, indexadas por rota e filtros."""

    def __init__(self, respostas):
        self.respostas = respostas

    def todos(self, caminho, **params):
        return self.respostas.get((caminho, tuple(sorted(params.items()))), [])


def test_votacoes_e_presenca():
    registro = {
        "id": 107,
        "__str__": "Ordem: Ordem do Dia/Expediente: 1 - Veto nº 1 de 2025 em 10ª Ordinária da 3ª Sessão Legislativa da 16ª Legislatura - Votação: Aprovado",
        "numero_votos_sim": 15,
        "numero_votos_nao": 0,
        "numero_abstencoes": 0,
        "data_hora": "2025-06-26T12:42:52-03:00",
        "materia": 17398,
    }
    simbolica = {**registro, "id": 108}
    falso = _SaplFalso({
        ("sessao/registrovotacao/", (("data_hora__year", 2025),)): [registro, simbolica],
        ("sessao/votoparlamentar/", (("data_hora__year", 2025),)): [
            {"votacao": 107, "parlamentar": 248, "voto": "Sim"},
            {"votacao": 107, "parlamentar": 999, "voto": "Não"},  # fora do cargo hoje
        ],
        ("sessao/sessaoplenaria/", (("data_inicio__year", 2025),)): [
            {"id": 1, "data_inicio": "2025-02-03"}, {"id": 2, "data_inicio": "2025-05-03"},
            {"id": 3, "data_inicio": "2025-08-03"}, {"id": 4, "data_inicio": "2025-09-03"},  # sem presença lançada
        ],
        ("sessao/sessaoplenariapresenca/", (("parlamentar", 248),)): [{"sessao_plenaria": 1}, {"sessao_plenaria": 2}, {"sessao_plenaria": 3}],
        ("sessao/sessaoplenariapresenca/", (("parlamentar", 250),)): [{"sessao_plenaria": 3}],
    })  # fmt: skip
    resultado = sapl.coletar_votacoes(falso, {2025}, {248, 250})
    assert [v["id_externo"] for v in resultado["votacoes"]] == ["107"]  # a simbólica não entra
    assert resultado["votacoes"][0]["materia"] == "Veto nº 1 de 2025"
    assert resultado["votos"] == [{"votacao": "107", "parlamentar": "248", "voto": "Sim"}]
    # 250 assumiu em julho: só conta a sessão 3 (a 4 não tem presença lançada).
    presenca = sapl.coletar_presenca(
        falso, {2025}, date(2026, 1, 1), {248: (None, None), 250: ("2025-07-01", None)}
    )
    assert presenca == {248: (3, 3), 250: (1, 1)}
    assert sapl.coletar_presenca(_SaplFalso({}), {2025}, date(2026, 1, 1), {248: (None, None)}) == {
        248: (None, None)
    }


def _deputado(id_externo, nome):
    return {"id_externo": id_externo, "nome": nome, "nome_completo": None, "partido": "PL", "foto_url": None,
            "email": None, "telefone": None, "titular": True, "em_exercicio": True, "inicio": "2023-02-01",
            "fim": "2027-01-31", "proposicoes_por_tipo": {"Indicação": 2}, "projetos": [], "sessoes": 4, "presencas": 4}  # fmt: skip


def _votacao(id_externo, data):
    return {"id_externo": id_externo, "materia": f"Veto nº {id_externo} de 2025", "resultado": "Aprovado",
            "sim": 2, "nao": 0, "abstencoes": 0, "data": data, "materia_id": None}  # fmt: skip


def test_comparar_na_mesma_casa(client, session):
    casa = {
        "base": "https://sapl.al.ac.leg.br/",
        "vereadores": [_deputado("1", "Ana"), _deputado("2", "Bia")],
        "votacoes": [_votacao("10", "2025-03-01"), _votacao("11", "2025-04-01"), _votacao("12", "2025-05-01")],
        "votos": [
            {"votacao": "10", "parlamentar": "1", "voto": "Sim"}, {"votacao": "10", "parlamentar": "2", "voto": "Sim"},
            {"votacao": "11", "parlamentar": "1", "voto": "Sim"}, {"votacao": "11", "parlamentar": "2", "voto": "Não"},
            # Uma delas não votou: não entra na conta.
            {"votacao": "12", "parlamentar": "1", "voto": "Sim"}, {"votacao": "12", "parlamentar": "2", "voto": "Não Votou"},
        ],
    }  # fmt: skip
    sapl.gravar(session, None, casa, uf="AC")
    sapl.gravar(
        session,
        None,
        {**casa, "vereadores": [_deputado("1", "Rui")], "votacoes": [], "votos": []},
        uf="RR",
    )
    session.flush()
    ids = {
        i["nome"]: i["id"]
        for uf in ("AC", "RR")
        for i in client.get(f"/estados/{uf}/assembleia").json()["itens"]
    }
    corpo = client.get("/comparar/local", params={"a": ids["Ana"], "b": ids["Bia"]}).json()
    assert (corpo["votacoes_em_comum"], corpo["iguais"]) == (2, 1)
    assert corpo["divergencias"][0]["materia"] == "Veto nº 11 de 2025"
    assert corpo["proposicoes_por_tipo"] == [{"tipo": "Indicação", "a": 2, "b": 2}]
    assert (
        client.get("/comparar/local", params={"a": ids["Ana"], "b": ids["Rui"]}).status_code == 422
    )
    assert (
        client.get("/comparar/local", params={"a": ids["Ana"], "b": ids["Ana"]}).status_code == 422
    )


def test_casar_nome_em_niveis_e_so_quando_unico():
    eleitos = [(1, "Alex de Madureira"), (2, "Dr Valdomiro Lopes"), (3, "Capitão Conte Lopes"),
               (4, "Alex Santana"), (5, "Leo Siqueira"), (6, "Caruso")]  # fmt: skip
    assert sapl.casar_nome(["Alex Madureira"], eleitos) == 1
    assert sapl.casar_nome(["Valdomiro Lopes"], eleitos) == 2
    assert sapl.casar_nome(["Conte Lopes"], eleitos) == 3
    assert sapl.casar_nome(["Camilo Santana"], eleitos) is None  # sobrenome solto não basta
    assert sapl.casar_nome(["Leonardo Siqueira"], eleitos) is None
    assert sapl.casar_nome(["Jorge Caruso"], eleitos) is None  # uma palavra só não basta
    # Ambíguo: "Lopes" e outra palavra em dois eleitos.
    assert (
        sapl.casar_nome(["Lopes Silva"], [(1, "Ana Lopes Silva"), (2, "Rui Lopes Silva")]) is None
    )


def test_item_sumido_ou_pagina_que_some_nao_derrubam_a_casa():
    import httpx

    def servidor(request):
        if "parlamentar/17" in request.url.path:
            return httpx.Response(404)
        if request.url.params.get("page") == "2":
            return httpx.Response(404)  # a lista encolheu entre as páginas
        return httpx.Response(200, json={"results": [{"id": 1}], "pagination": {"next_page": 2}})

    with httpx.Client(transport=httpx.MockTransport(servidor)) as client:
        casa = sapl.Sapl("https://sapl.x.leg.br/", client)
        sapl.PAUSA, pausa = 0, sapl.PAUSA
        try:
            assert casa.talvez("parlamentares/parlamentar/17/") is None
            assert casa.todos("materia/autoria/", autor=1) == [{"id": 1}]
        finally:
            sapl.PAUSA = pausa
    longo = "Ordem: 1 - Requerimento nº 1 de 2025 em 1ª Ordinária - Votação: " + "Aprovado " * 20
    assert len(sapl.ler_registro(longo)[1]) == 60
