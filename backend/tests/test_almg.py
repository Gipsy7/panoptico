# ruff: noqa: E501  (recortes de respostas reais da API da ALMG)
from decimal import Decimal

from ingestion.assembleias import almg
from ingestion.camaras import sapl

PL = {
    "siglaTipoProjeto": "PL",
    "numero": "5450",
    "ano": "2025",
    "ementa": "Dispõe sobre o  couvert artístico.",
    "dataPublicacao": "2026-04-09",
    "autor": "Deputado Professor Cleiton   PV\nDeputado Zé Guilherme   PP\n",
    "matricula": "26119\n26105\n",
}
DO_GOVERNADOR = {
    "siglaTipoProjeto": "PL",
    "numero": "1",
    "ano": "2025",
    "ementa": "x",
    "autor": "Governador do Estado",
}
RQN = {"siglaTipoProjeto": "RQN", "numero": "9", "ano": "2025", "matricula": "26105\n"}


def test_autoria_principal_coautor_e_sem_matricula():
    assert almg.autores(PL) == ["26119", "26105"]
    assert almg.autores(DO_GOVERNADOR) == []
    deputados = almg.distribuir({"PL": [PL, DO_GOVERNADOR], "RQN": [RQN]}, {"26119", "26105"})
    cleiton, ze = deputados["26119"], deputados["26105"]
    assert cleiton["projetos"][0]["primeiro_autor"] and not ze["projetos"][0]["primeiro_autor"]
    assert cleiton["projetos"][0]["url"] == "https://www.almg.gov.br/projetos-de-lei/PL/5450/2025"
    assert cleiton["projetos"][0]["ementa"] == "Dispõe sobre o couvert artístico."
    assert ze["contagem"] == {"Projeto de Lei": 1, "Requerimento": 1}
    assert almg._data({"@class": "sql-timestamp", "$": "2025-02-03"}) == "2025-02-03"


def _deputado(id_externo, nome, gastos):
    return {"id_externo": id_externo, "nome": nome, "nome_completo": None, "partido": "PV", "foto_url": None,
            "email": None, "telefone": None, "titular": True, "em_exercicio": True, "inicio": "2023-02-01", "fim": None,
            "proposicoes_por_tipo": {}, "projetos": [], "sessoes": None, "presencas": None, "gastos": gastos}  # fmt: skip


def test_gastos_e_fonte_propria(client, session):
    gasto = {
        "ano": 2025,
        "mes": 5,
        "categoria": "Combustível e lubrificante",
        "valor": Decimal("1978.65"),
    }
    casa = {"base": almg.SITE, "vereadores": [_deputado("12193", "Adalclever Lopes", [gasto]), _deputado("1", "Sem Gasto", [])],
            "votacoes": [], "votos": []}  # fmt: skip
    sapl.gravar(session, None, casa, uf="MG")
    session.flush()
    corpo = client.get("/estados/MG/assembleia").json()
    assert corpo["fonte_nome"] == "Dados abertos da Assembleia de Minas Gerais (ALMG)"
    adalclever = next(i for i in corpo["itens"] if i["nome"] == "Adalclever Lopes")
    detalhe = client.get(f"/vereadores/{adalclever['id']}").json()
    # Média da casa: (1978,65 + 0) / 2; quem não pediu reembolso entra com zero.
    assert detalhe["gastos"]["total"] == 1978.65 and detalhe["gastos"]["media_casa"] == 989.325
    assert detalhe["gastos"]["ate_mes"] == 5
    assert detalhe["presenca"] is None
