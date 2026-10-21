"""Discursos em Plenário (Câmara e Senado): extrator de citações, ligação ao projeto do dia,
recorte por dia de votação nominal, idempotência e --de-raw.

As amostras em tests/fixtures/discursos/ são respostas reais recortadas das APIs (fevereiro de
2025; a transcrição foi retirada). Os casos de 3 ou mais matérias são montados no teste."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Discurso, FonteIngestao, Parlamentar, Votacao
from ingestion import comum
from ingestion import discursos_comum as dc
from ingestion.camara import discursos as camara
from ingestion.senado import discursos as senado

PASTA = Path(__file__).parent / "fixtures" / "discursos"
DEPUTADO = "220574"  # Cabo Gilberto Silva, autor das falas da amostra


def _bruto(nome: str) -> dict:
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


def _ingestao(session, fonte="teste"):
    ingestao = FonteIngestao(fonte=fonte, url="https://exemplo", arquivo_raw="x.json")
    session.add(ingestao)
    session.flush()
    return ingestao


def _parlamentar(session, casa, id_externo, nome="Fulano"):
    p = Parlamentar(
        casa=casa,
        id_externo=id_externo,
        nome_parlamentar=nome,
        uf="PB",
        fonte_url="https://exemplo",
        atualizado_em=datetime.now(UTC),
    )
    session.add(p)
    session.flush()
    return p


def _votacao(session, casa, id_externo, dia, proposicao, proposicao_id):
    session.add(
        Votacao(
            casa=casa,
            id_externo=id_externo,
            data=dia,
            descricao="Votação",
            proposicao=proposicao,
            proposicao_id_externo=proposicao_id,
        )
    )
    session.flush()


def _cenario_camara(session):
    _parlamentar(session, "camara", DEPUTADO, "Cabo Gilberto Silva")
    # 12/02 e 18/02 tiveram votação nominal; 04/02 não (no cenário).
    _votacao(session, "camara", "v1", date(2025, 2, 12), "PL 2215/2024", "2470000")
    _votacao(session, "camara", "v2", date(2025, 2, 18), "PLP 223/2023", "2380000")
    _votacao(session, "camara", "v3", date(2025, 2, 18), "PL 4187/2024 (Nº Anterior: x)", "2480000")


def _carregar_camara(session, payload=None):
    return camara.carregar(
        session, payload or _bruto("camara_discursos.json"), _ingestao(session, camara.FONTE)
    )


# ---- extrator de citações ----


def test_citacao_de_uma_materia_por_extenso():
    texto = (
        "O Deputado discutiu o Projeto de Lei n° 2.215, de 2024, que institui o Dia Nacional "
        "para a Ação Climática."
    )
    assert dc.citacoes(texto) == {"PL 2215/2024"}


def test_citacao_de_duas_materias_e_siglas():
    texto = (
        "Orientou a bancada na votação do Projeto de Lei Complementar nº 223, de 2023, e "
        "criticou o PL nº&nbsp;5.063 de 2023."
    )
    assert dc.citacoes(texto) == {"PLP 223/2023", "PL 5063/2023"}


def test_citacao_de_tres_ou_mais_materias_e_balanco():
    texto = (
        "Balanço da semana: PL 100/2025, a Medida Provisória nº 1.300, de 2025, e a "
        "Proposta de Emenda à Constituição nº 3, de 2021."
    )
    citadas = dc.citacoes(texto)
    assert citadas == {"PL 100/2025", "MPV 1300/2025", "PEC 3/2021"}
    assert dc.ligar(citadas, {"PL 100/2025": "1", "PEC 3/2021": "2"}) is None


def test_citacao_ignora_lei_e_texto_sem_materia():
    assert dc.citacoes("Altera a Lei nº 13.105, de 16 de março de 2015.") == set()
    assert dc.citacoes(None) == set()


def test_resumo_do_senado_com_sigla_entre_parenteses():
    texto = "Orientação à bancada sobre o Projeto de Lei Complementar (PLP) nº 22, de 2025."
    assert dc.citacoes(texto) == {"PLP 22/2025"}


def test_rotulo_tira_sufixo():
    assert dc.rotulo("PL 2159/2021 (Nº Anterior: PL 3729/2004)") == "PL 2159/2021"
    assert dc.rotulo("PLP 235/2019 (Substitutivo-CD)") == "PLP 235/2019"
    assert dc.rotulo(None) is None


# ---- Câmara ----


def test_camara_liga_ao_projeto_do_dia(session):
    _cenario_camara(session)
    _carregar_camara(session)
    por_projeto = dict(
        session.execute(
            select(Discurso.proposicao_id_externo, func.count()).group_by(
                Discurso.proposicao_id_externo
            )
        ).all()
    )
    assert por_projeto["2470000"] == 2  # PL 2215/2024: discussão e orientação
    assert por_projeto["2380000"] == 2  # PLP 223/2023: encaminhamento e orientação
    assert por_projeto["2480000"] == 1  # PL 4187/2024 (rótulo com sufixo)
    # PL 3987/2023 e PL 3875/2024 são citados, mas não foram votados no dia: sem projeto.
    assert por_projeto[None] == 2
    um = session.scalars(
        select(Discurso).where(Discurso.proposicao_id_externo == "2470000")
    ).first()
    assert um.casa == "camara" and um.materias_citadas == 1
    assert um.fase in {"Ordem do Dia", "Breves Comunicações"} and um.tipo
    assert um.sumario and "transcricao" not in um.sumario.lower()
    assert um.parlamentar_id is not None and um.data_hora.date() == um.data


def test_camara_descarta_dia_sem_votacao_e_discurso_sem_materia(session):
    _cenario_camara(session)
    _carregar_camara(session)
    dias = set(session.scalars(select(Discurso.data)))
    assert dias == {date(2025, 2, 12), date(2025, 2, 18)}  # 04/02 não teve votação


def test_camara_so_guarda_quem_esta_na_tabela(session):
    _votacao(session, "camara", "v1", date(2025, 2, 12), "PL 2215/2024", "2470000")
    with pytest.raises(ValueError):  # sem o deputado, nada casa: carga completa aborta
        _carregar_camara(session, _bruto("camara_discursos.json") | {"completa": True})
    assert _carregar_camara(session) == 0  # incremental: nada a gravar, nada apagado


def test_camara_carga_idempotente(session):
    _cenario_camara(session)
    primeira = _carregar_camara(session)
    segunda = _carregar_camara(session)
    assert primeira == segunda == session.scalar(select(func.count()).select_from(Discurso))


def test_camara_recarga_apaga_so_a_janela(session):
    _cenario_camara(session)
    _carregar_camara(session)
    antes = session.scalar(select(func.count()).select_from(Discurso))
    # Janela de um dia só (12/02): os de 18/02 ficam; o de 12/02 é reinserido.
    payload = _bruto("camara_discursos.json")
    payload["inicio"] = payload["fim"] = "2025-02-12"
    _carregar_camara(session, payload)
    assert session.scalar(select(func.count()).select_from(Discurso)) == antes


def test_camara_chave_estavel_e_sem_duplicata(session):
    registros = camara.normalizar(_bruto("camara_discursos.json"))
    ids = [r["id_externo"] for r in registros]
    assert len(ids) == len(set(ids))
    assert all(i.startswith(f"{DEPUTADO}:2025-02-") for i in ids)
    repetido = {
        "deputados": {DEPUTADO: [_bruto("camara_discursos.json")["deputados"][DEPUTADO][0]] * 2}
    }
    ids = [r["id_externo"] for r in camara.normalizar(repetido)]
    assert ids[0] != ids[1]  # dois no mesmo instante ganham ocorrências diferentes


# ---- regras de ligação (casa a casa e 3+ matérias) ----


def _discurso(id_externo, citadas, dia=date(2025, 2, 18)):
    return {
        "id_externo": id_externo,
        "parlamentar_id": None,
        "data": dia,
        "data_hora": None,
        "sessao_id_externo": None,
        "fase": None,
        "tipo": None,
        "sumario": "x",
        "url_texto": None,
        "url_video": None,
        "citadas": citadas,
    }


def test_ligacao_so_com_uma_ou_duas_materias(session):
    _votacao(session, "camara", "v1", date(2025, 2, 18), "PL 1/2025", "1")
    _votacao(session, "camara", "v2", date(2025, 2, 18), "PL 2/2025", "2")
    discursos = [
        _discurso("a", {"PL 1/2025"}),
        _discurso("b", {"PL 1/2025", "PL 9/2025"}),  # duas citadas, só uma votada: liga
        _discurso("c", {"PL 1/2025", "PL 2/2025"}),  # duas votadas no dia: ambíguo, sem projeto
        _discurso("d", {"PL 1/2025", "PL 2/2025", "PL 9/2025"}),  # três: discurso do dia
        _discurso("e", set()),  # sem matéria: fora
    ]
    dc.recarregar_discursos(
        session, "camara", date(2025, 2, 1), date(2025, 2, 28), discursos, _ingestao(session)
    )
    linhas = {d.id_externo: d for d in session.scalars(select(Discurso))}
    assert set(linhas) == {"a", "b", "c", "d"}
    assert linhas["a"].proposicao_id_externo == "1"
    assert linhas["b"].proposicao_id_externo == "1"
    assert linhas["c"].proposicao_id_externo is None and linhas["c"].materias_citadas == 2
    assert linhas["d"].proposicao_id_externo is None and linhas["d"].materias_citadas == 3


# ---- Senado ----


def _cenario_senado(session, payload):
    codigos = {
        p["CodigoParlamentar"]
        for r in payload["respostas"]
        for s in r["DiscursosSessao"]["Sessoes"]["Sessao"]
        for p in s["Pronunciamentos"]["Pronunciamento"]
        if p.get("CodigoParlamentar")
    }
    for codigo in codigos:
        _parlamentar(session, "senado", codigo)
    _votacao(session, "senado", "sv1", date(2025, 2, 19), "PLP 22/2025", "163000")
    _votacao(
        session, "senado", "sv2", date(2025, 2, 3), "PL 1/2025", "163001"
    )  # dia da sessão do CN


def test_senado_liga_por_sessao_e_materia(session):
    payload = _bruto("senado_discursos.json")
    _cenario_senado(session, payload)
    total = senado.carregar(session, payload, _ingestao(session, senado.FONTE))
    linhas = session.scalars(select(Discurso)).all()
    assert total == len(linhas) == 3  # 3 citam o PLP 22/2025; 1 não cita matéria e cai
    assert {d.sessao_id_externo for d in linhas} == {"450520"}  # a sessão do Congresso fica fora
    assert {d.proposicao_id_externo for d in linhas} == {"163000"}
    assert {d.data for d in linhas} == {date(2025, 2, 19)}
    d = linhas[0]
    assert d.casa == "senado" and d.tipo and d.fase and d.url_texto.startswith("https://")
    assert d.sumario.startswith(("Considerações", "Orientação", "Discussão", "Como Relator"))
    assert d.url_video is None and d.data_hora is None


def test_senado_idempotente_e_sem_autor_externo(session):
    payload = _bruto("senado_discursos.json")
    _cenario_senado(session, payload)
    # Fala de convidado (sem CodigoParlamentar) não entra.
    sessao = payload["respostas"][0]["DiscursosSessao"]["Sessoes"]["Sessao"][0]
    externo = dict(sessao["Pronunciamentos"]["Pronunciamento"][0], CodigoPronunciamento="1")
    externo.pop("CodigoParlamentar")
    sessao["Pronunciamentos"]["Pronunciamento"].append(externo)
    senado.carregar(session, payload, _ingestao(session))
    senado.carregar(session, payload, _ingestao(session))
    assert session.scalar(select(func.count()).select_from(Discurso)) == 3


def test_senado_sessao_unica_vem_como_objeto():
    sessao = _bruto("senado_discursos.json")["respostas"][0]["DiscursosSessao"]["Sessoes"][
        "Sessao"
    ][0]
    um = {"inicio": "2025-02-01", "fim": "2025-02-28", "respostas": [
        {"DiscursosSessao": {"Sessoes": {"Sessao": sessao}}}  # objeto, não lista
    ]}  # fmt: skip
    assert len(senado.normalizar(um)) >= 1


# ---- janela incremental ----


def test_janela_incremental(session):
    hoje = date(2026, 10, 21)
    piso = date(2025, 1, 1)
    assert dc.inicio_incremental(session, "fonte_nova", 7, piso, hoje) == (piso, True)
    session.add(
        FonteIngestao(
            fonte="fonte_x",
            url="u",
            arquivo_raw="r",
            status="ok",
            concluido_em=datetime(2026, 10, 20, 12, tzinfo=UTC),
        )
    )
    session.flush()
    assert dc.inicio_incremental(session, "fonte_x", 7, piso, hoje) == (date(2026, 10, 13), False)
    assert dc.inicio_incremental(session, "fonte_x", 21, piso, hoje) == (date(2026, 9, 29), False)


# ---- --de-raw, com commit no banco de teste ----


@pytest.fixture
def banco(engine, tmp_path, monkeypatch):
    fabrica = sessionmaker(bind=engine)
    monkeypatch.setattr(comum, "SessionLocal", fabrica)
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    with fabrica() as s:
        _cenario_camara(s)
        s.commit()
    yield fabrica
    with fabrica() as s:
        s.execute(delete(Discurso))
        s.execute(delete(Votacao).where(Votacao.id_externo.in_(["v1", "v2", "v3"])))
        s.execute(delete(Parlamentar).where(Parlamentar.id_externo == DEPUTADO))
        s.execute(delete(FonteIngestao).where(FonteIngestao.fonte == camara.FONTE))
        s.commit()


def test_de_raw_reprocessa_sem_rede(banco):
    arquivo = PASTA / "camara_discursos.json"
    # Sem respx: qualquer chamada de rede estouraria; --de-raw só lê o arquivo.
    primeira = camara.executar(de_raw=arquivo)
    segunda = camara.executar(de_raw=arquivo)
    assert primeira == segunda == 7
    with banco() as s:
        assert s.scalar(select(func.count()).select_from(Discurso)) == 7
        ingestoes = s.scalars(
            select(FonteIngestao).where(FonteIngestao.fonte == camara.FONTE)
        ).all()
        assert [i.status for i in ingestoes] == ["ok", "ok"]
        assert ingestoes[0].concluido_em > datetime.now(UTC) - timedelta(minutes=5)


def test_camara_pede_mes_a_mes_e_pula_so_o_dia_com_erro_da_fonte(monkeypatch):
    """A API da Câmara dá 500 num período com registro defeituoso (deputado 141456, outubro de
    2026). A coleta divide o período até o dia e deixa só esse dia de fora."""
    import httpx

    from ingestion.camara import discursos as camara

    pedidos = []

    def falso(client, id_deputado, inicio, fim, tentativas=1):
        pedidos.append((inicio, fim))
        if inicio <= date(2026, 10, 3) <= fim:
            resposta = httpx.Response(500, request=httpx.Request("GET", "https://x"))
            raise httpx.HTTPStatusError("500", request=resposta.request, response=resposta)
        return [{"dataHoraInicio": f"{inicio}T10:00"}]

    monkeypatch.setattr(camara, "_baixar_paginas", falso)
    falhas = []
    discursos = camara.baixar_deputado(
        None, "141456", date(2026, 9, 20), date(2026, 10, 21), falhas
    )
    assert falhas == [{"deputado": "141456", "dia": "2026-10-03"}]
    assert (date(2026, 9, 20), date(2026, 9, 30)) in pedidos  # primeiro, o mês de setembro
    assert discursos  # os outros dias vieram


def test_senado_pede_um_mes_do_calendario_por_vez(monkeypatch):
    from ingestion.senado import discursos as senado

    urls = []
    monkeypatch.setattr(senado.comum, "get_json", lambda client, url, **k: urls.append(url) or {})
    monkeypatch.setattr(senado.time, "sleep", lambda s: None)
    senado.baixar(None, date(2025, 2, 1), date(2025, 3, 15), True)
    assert urls[0].endswith("/20250201/20250228")
    assert urls[1].endswith("/20250301/20250315")


def test_resumo_sem_html():
    from ingestion import discursos_comum as dc

    assert (
        dc.limpar_texto("O Deputado discutiu o&nbsp;Projeto de Lei Complementar nº 74")
        == "O Deputado discutiu o Projeto de Lei Complementar nº 74"
    )
    assert dc.limpar_texto("<p>Defendeu a&amp;nbsp;aprovação.</p>") == "Defendeu a aprovação."
    assert dc.limpar_texto("  ") is None
