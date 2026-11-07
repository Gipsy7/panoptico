"""Tipo de votação (mérito ou procedimento), calendário e recorte no perfil. As descrições são
textos reais publicados pela Câmara e pelo Senado (acervo, 2025-2026)."""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import Parlamentar, Votacao
from app.services import tipo_votacao as tv
from app.services.projeto_detalhe import escolher_principal
from app.services.projeto_etapas import etapa_do_passo
from ingestion import resumos
from ingestion import votacoes_comum as vc
from tests.test_api import _ingestao, _popular

MERITO = [
    # Texto-base e substitutivo
    "Aprovado o Projeto de Lei nº 2.215, de 2024. Sim: 273; Não: 136; Total: 409.",
    "Aprovada a Subemenda Substitutiva Global ao Projeto de Lei Complementar nº 167, de 2024, "
    "adotada pelo relator da Comissão de Indústria, Comércio e Serviços.",
    # PEC em 1º turno, nas duas Casas
    "Aprovado, em primeiro turno, o Substitutivo da Comissão Especial à Proposta de Emenda "
    "Constitucional nº 66, de 2023.",
    "Votação nominal da Proposta de Emenda à Constituição nº 18, de 2024, nos termos do parecer "
    "(1º Turno).",
    # Emenda e destaque (DVS: "Mantido o texto" / "Suprimido o texto")
    "Rejeitada a Emenda de Plenário nº 2. Sim: 57; Não: 331; Total: 388.",
    "Mantido o texto. Sim: 386; Não: 27; Total: 413.",
    "Suprimido o texto. Sim: 152; Não: 220; Abstenção: 1; Total: 373.",
    "Rejeitado o Destaque. Sim: 159; Não: 243; Total: 402.",
    "Votação nominal do Art. 2º do Projeto de Lei de Conversão nº 2, de 2025, destacado.",
    # Redação final
    "Aprovada a Redação Final assinada pelo relator, Luiz Fernando Faria (PSD-MG).",
    # Medida provisória e escolha de autoridade no Senado
    "Aprovada a Medida Provisória nº 1.268, de 2024. Sim: 317; Não: 92; Total: 411.",
    "Votação nominal da Mensagem nº 3, de 2025 - Rodrigo de Lima Baena Soares (Alemanha).",
    "Votação nominal do Ofício nº 12, de 2025 - Fabio Francisco Esteves (CNJ).",
]
PROCEDIMENTO = [
    "Aprovado o Requerimento de Urgência (Art. 155 do RICD). Sim: 266; Não: 140; Total: 408.",
    "Rejeitado o Requerimento. Sim: 125; Não: 236; Abstenção: 2; Total: 363.",
    "(Votação nominal do Requerimento nº 451, de 2025, que solicita urgência para o Projeto de "
    "Lei Complementar nº 177, de 2023).",
    "Solicita urgência para o Projeto de Lei nº 2.234, de 2022",
    "Aprovado o Requerimento nº 2.779/2025, dos Senhores Líderes, que solicita a quebra de "
    "interstício de 5 sessões previsto no § 6º do art. 202 do RICD",
    "Rejeitada a preferência. Sim: 129; Não: 262; Total: 391.",
    "Rejeitado o Recurso nº 7/2024 (art. 58, § 1º c/c art. 132, § 2º, RICD).",
    "Aprovado, em apreciação preliminar, o Parecer da Comissão Mista de Planos, Orçamentos "
    "Públicos e Fiscalização, na parte em que manifesta opinião favorável quanto ao atendimento "
    "dos pressupostos constitucionais",
    "Votação nominal da decisão da Presidência na Questão de Ordem apresentada pelo Senador X.",
    "Rejeitada a inclusão. Sim: 119; Não: 310; Abstenção: 1; Total: 430.",
    # Sem como classificar: fica em procedimento, contado à parte
    "Resultado. Sim: 182; Não: 182; Abstenção: 2; Total: 366.",
    "",
]


@pytest.mark.parametrize("descricao", MERITO)
def test_merito(descricao):
    assert tv.classificar(descricao) == tv.MERITO


@pytest.mark.parametrize("descricao", PROCEDIMENTO)
def test_procedimento(descricao):
    assert tv.classificar(descricao) == tv.PROCEDIMENTO


def test_texto_inteiro_para_a_votacao_principal():
    # Texto-base com destaques para depois e PEC "na forma da emenda aglutinativa": texto inteiro.
    assert tv.eh_texto_inteiro(
        "Aprovada, em segundo turno, a Proposta de Emenda à Constituição nº 66, de 2023, "
        "ressalvado o destaque."
    )
    assert tv.eh_texto_inteiro(
        "Aprovada, em primeiro turno, a Proposta de Emenda à Constituição nº 383, de 2017, na "
        "forma da Emenda Aglutinativa nº 1."
    )
    assert tv.eh_texto_inteiro("Aprovada a Redação Final assinada pela relatora.")
    # Emenda, destaque e procedimento: não.
    for parte in ("Mantido o texto.", "Aprovada a Emenda de Plenário nº 2.", PROCEDIMENTO[0]):
        assert not tv.eh_texto_inteiro(parte)


def test_votacao_principal_ignora_o_destaque_depois_do_texto(session):
    _popular(session)
    texto = Votacao(
        casa="camara", id_externo="1-1", data=date(2026, 3, 1), secreta=False,
        descricao="Aprovado o Projeto de Lei nº 1, de 2026, ressalvados os destaques.",
    )  # fmt: skip
    destaque = Votacao(
        casa="camara", id_externo="1-2", data=date(2026, 3, 1), secreta=False,
        descricao="Mantido o texto.",
    )  # fmt: skip
    assert escolher_principal([texto, destaque]) is texto


def test_etapa_votado_no_plenario_nao_conta_procedimento():
    assert etapa_do_passo("Votação (Plenário)", "Aprovado o projeto.") == "Votado no Plenário"
    assert etapa_do_passo("Votação (Plenário)", "Aprovado requerimento de urgência.") != (
        "Votado no Plenário"
    )
    assert etapa_do_passo("Votação (Plenário)", "Rejeitado o recurso.") != "Votado no Plenário"


# --- Carga, calendário e perfil ---------------------------------------------------------------

DESCRICOES = {
    "v0": "Aprovado o Projeto de Lei nº 1, de 2026. Sim: 2; Não: 1; Total: 3.",
    "v1": "Aprovado o Requerimento de Urgência (Art. 155 do RICD).",
    "v2": "Mantido o texto.",
    "v3": "Rejeitado o Requerimento.",
}


def _cenario(session):
    """3 deputados e 4 votações (2 de mérito, 2 de procedimento), com orientação do Governo:
    v0 mérito  Governo Sim | A Sim  B Sim  C Não
    v1 proced. Governo Não | A Sim  B Não  C Não
    v2 mérito  Governo Não | A Não  B Sim  C Sim
    v3 proced. Governo Sim | A Sim  B Sim
    """
    _popular(session)
    a, b, c = session.scalars(
        select(Parlamentar).where(Parlamentar.casa == "camara").order_by(Parlamentar.id)
    ).all()
    datas = {"v0": date(2026, 3, 3), "v1": date(2026, 3, 4), "v2": date(2026, 3, 5),
             "v3": date(2026, 3, 9)}  # fmt: skip
    votacoes = [
        {"id_externo": v, "data": datas[v], "descricao": d, "proposicao": "PL 1/2026",
         "proposicao_id_externo": "1", "secreta": False}
        for v, d in DESCRICOES.items()
    ]  # fmt: skip
    tabela = {
        "v0": {a: "Sim", b: "Sim", c: "Não"},
        "v1": {a: "Sim", b: "Não", c: "Não"},
        "v2": {a: "Não", b: "Sim", c: "Sim"},
        "v3": {a: "Sim", b: "Sim"},
    }
    votos = [
        {"id_externo_votacao": v, "parlamentar_id": p.id, "voto": voto, "partido": "PX"}
        for v, linha in tabela.items()
        for p, voto in linha.items()
    ]
    orientacoes = [
        {"id_externo_votacao": v, "bancada": "Governo", "orientacao": o}
        for v, o in (("v0", "Sim"), ("v1", "Não"), ("v2", "Não"), ("v3", "Sim"))
    ]
    vc.recarregar_votacoes(
        session, "camara", 2026, votacoes, votos, _ingestao(session), orientacoes
    )
    session.execute(resumos.ResumoParlamentar.__table__.insert(), resumos.calcular(session, [2026]))
    session.flush()
    return a, b, c


def test_carga_grava_o_tipo(session):
    _cenario(session)
    tipos = dict(session.execute(select(Votacao.id_externo, Votacao.tipo_votacao)).all())
    assert tipos == {"v0": "merito", "v1": "procedimento", "v2": "merito", "v3": "procedimento"}


def test_calendario_conta_por_dia_e_filtra_o_dia(client, session):
    _cenario(session)
    corpo = client.get("/votacoes/calendario?casa=camara").json()
    assert (corpo["ano"], corpo["mes"]) == (2026, 3)  # mês mais recente com votação
    assert corpo["totais"] == {"todas": 4, "merito": 2, "procedimento": 2}
    assert [(d["data"], d["todas"]) for d in corpo["dias"]] == [
        ("2026-03-03", 1), ("2026-03-04", 1), ("2026-03-05", 1), ("2026-03-09", 1),
    ]  # fmt: skip
    assert corpo["por_casa"] == {"camara": 4, "senado": 0}
    assert corpo["mes_anterior"] is None and corpo["mes_seguinte"] is None
    assert corpo["fonte_nome"].startswith("Votações nominais do Plenário")
    # Lista do mês, mais recente primeiro, com placar contado dos votos.
    lista = corpo["lista"]
    assert [i["id_externo"] for i in lista["itens"]] == ["v3", "v2", "v1", "v0"]
    assert lista["itens"][3]["placar"] == {"sim": 2, "nao": 1, "abstencao": 0}
    assert lista["itens"][3]["link"] == "/votacao/camara/v0"

    so_texto = client.get("/votacoes/calendario?casa=camara&tipo=merito").json()["lista"]
    assert so_texto["total"] == 2
    assert so_texto["contagem_tipos"] == {"todas": 4, "merito": 2, "procedimento": 2}
    assert {i["tipo"] for i in so_texto["itens"]} == {"merito"}

    dia = client.get("/votacoes/calendario?casa=camara&ano=2026&mes=3&dia=2026-03-04").json()
    assert dia["dia"] == "2026-03-04"
    assert [i["id_externo"] for i in dia["lista"]["itens"]] == ["v1"]
    assert dia["lista"]["contagem_tipos"] == {"todas": 1, "merito": 0, "procedimento": 1}

    assert client.get("/votacoes/calendario?casa=senado").status_code == 404
    vazio = client.get("/votacoes/calendario?casa=camara&ano=2026&mes=5").json()
    assert vazio["dias"] == [] and vazio["mes_anterior"] == {"ano": 2026, "mes": 3}


def test_perfil_recorte_merito_recalcula_numero_e_media(client, session):
    a, b, c = _cenario(session)
    todas = client.get(f"/parlamentares/{a.id}/votos").json()
    assert todas["tipo"] == "todas"
    assert todas["governo"] == {"iguais": 3, "total": 4, "percentual": 75.0}
    assert todas["contagem_tipos"] == {"todas": 4, "merito": 2, "procedimento": 2}

    merito = client.get(f"/parlamentares/{a.id}/votos?tipo=merito").json()
    assert merito["tipo"] == "merito"
    # A: v0 igual (Sim) e v2 igual (Não) -> 2 de 2.
    assert merito["governo"] == {"iguais": 2, "total": 2, "percentual": 100.0}
    # Média da Câmara no mesmo recorte: A 100%, B 1 de 2 (50%), C 0 de 2 (0%) -> 50,0%.
    assert merito["media_governo"] == 50.0
    assert merito["total"] == 2
    assert {i["tipo"] for i in merito["itens"]} == {"merito"}
    # Os números de todas as votações continuam à mão para o resumo do topo.
    assert merito["todas"]["governo"] == todas["governo"]
    assert merito["todas"]["media_governo"] == todas["media_governo"]
