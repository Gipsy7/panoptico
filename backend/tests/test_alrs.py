# ruff: noqa: E501  (recortes de respostas reais dos portais da ALRS)
import html
import json
from datetime import date

import respx

from ingestion.assembleias import alrs

LISTA = {"lista": [
    {"codigoPro": 2557, "idDeputado": 2144, "nomeDeputado": "Adão Pretto Filho", "emailDeputado": "adao.prettofilho@al.rs.gov.br", "telefoneDeputado": None, "siglaPartido": "PT", "codStatus": 1, "fotoGrandeDeputado": "https://ww2.al.rs.gov.br/filerepository/fotografias/2023/3/24/360297_G.jpg"},
    {"codigoPro": 13, "idDeputado": 13, "nomeDeputado": "Adriana Lara ", "emailDeputado": "adriana.lara@al.rs.gov.br", "telefoneDeputado": "(51) 32101725", "siglaPartido": "PL", "codStatus": 1, "fotoGrandeDeputado": None},
    {"codigoPro": 14, "idDeputado": 14, "nomeDeputado": "Licenciado", "siglaPartido": "PL", "codStatus": 2},
]}  # fmt: skip


def _item(dado: dict) -> str:
    """Como o portal escreve o registro: JSON com \\uXXXX dentro de um atributo HTML."""
    return "<article data-item='" + html.escape(json.dumps(dado), quote=True) + "'>\n</article>"


def test_deputados_da_api():
    assert [(d["id"], d["nome"], d["partido"]) for d in alrs.deputados(LISTA)] == [
        ("2144", "Adão Pretto Filho", "PT"),
        ("13", "Adriana Lara", "PL"),  # espaço sobrando no fim do nome
    ]


PROPOSICOES = [
    {"siglaTipoProposicao": "PL", "nroProposicao": "1", "anoProposicao": "2026", "nomeProponente": "Deputado(a) Adriana Lara", "proposicaoId": "16a8ea46-010c", "dthProtocolo": "03/02/2026", "ementa": "Institui   a Política Estadual\nde Saúde Mental."},
    {"siglaTipoProposicao": "PL", "nroProposicao": "10", "anoProposicao": "2026", "nomeProponente": "Deputado(a) Adão Pretto Filho + 3 Deputado(s)", "proposicaoId": "7300e865", "dthProtocolo": "05/02/2026", "ementa": "X"},
    {"siglaTipoProposicao": "PL", "nroProposicao": "3", "anoProposicao": "2026", "nomeProponente": "Poder Executivo", "proposicaoId": "a", "dthProtocolo": "05/02/2026", "ementa": "Do governador"},
    {"siglaTipoProposicao": "RC", "nroProposicao": "5", "anoProposicao": "2026", "nomeProponente": "Deputado(a) Adriana Lara", "proposicaoId": "b", "dthProtocolo": "05/02/2026", "ementa": "Requer"},
    {"siglaTipoProposicao": "PL", "nroProposicao": "99", "anoProposicao": "2026", "nomeProponente": "Deputado(a) Ex-Deputado", "proposicaoId": "c", "dthProtocolo": "05/02/2026", "ementa": "Já saiu"},
    {"siglaTipoProposicao": "CON", "nroProposicao": "7", "anoProposicao": "2026", "nomeProponente": "Deputado(a) Adriana Lara", "proposicaoId": "d", "dthProtocolo": "05/02/2026", "ementa": "Convênio"},
]  # fmt: skip


def test_proposicoes_de_autoria():
    por = alrs.distribuir(PROPOSICOES, {"Adão Pretto Filho", "Adriana Lara"})
    adriana = por["Adriana Lara"]
    assert adriana["contagem"] == {"Projeto de Lei": 1, "Requerimento Comum": 1}
    projeto = adriana["projetos"][0]
    assert (projeto["id_externo"], projeto["numero"], projeto["data_apresentacao"]) == (
        "PL-1-2026",
        1,
        "2026-02-03",
    )
    assert projeto["ementa"] == "Institui a Política Estadual de Saúde Mental."
    assert projeto["url"] == "https://ww4.al.rs.gov.br/proposicao/PL/1/2026/16a8ea46-010c"
    # "Fulano + 3 Deputado(s)": o primeiro nome é o autor principal.
    assert por["Adão Pretto Filho"]["contagem"] == {"Projeto de Lei": 1}


VOTOS = _item({"nomeDeputado": "Adão Pretto Filho", "dataVotacao": "25/08/2026 00:00", "tipoProjeto": "VT ", "numProposicao": 599, "anoProposicao": 2023, "materia": "Encaminha Veto Total ao Projeto de Lei nº 599/2023.", "voto": "Não", "resultadoVotacao": "Rejeitado"}) + _item({"nomeDeputado": "Adão Pretto Filho", "dataVotacao": "26/08/2026 00:00", "tipoProjeto": "PL ", "numProposicao": 7, "anoProposicao": 2026, "materia": "Dispõe sobre X.", "voto": "Sim", "resultadoVotacao": "Aprovado"})  # fmt: skip


def test_votos_e_votacoes():
    adao = alrs.votos_da_pagina(VOTOS)
    assert [(v["chave"], v["voto"]) for v in adao] == [
        ("260825VT599/2023", "Não"),
        ("260826PL7/2026", "Sim"),
    ]
    assert adao[0]["materia"] == "VT 599/2023: Encaminha Veto Total ao Projeto de Lei nº 599/2023."
    adriana = [
        {**adao[0], "voto": "Sim"},
        {**adao[0], "voto": "Não"},
        {**adao[1], "voto": "Abstenção"},
    ]
    votacoes, votos = alrs.votacoes({"2144": adao, "13": adriana})
    por_chave = {v["id_externo"]: v for v in votacoes}
    # O segundo voto de Adriana na mesma votação (destaque) não conta; vale o primeiro.
    assert (por_chave["260825VT599/2023"]["sim"], por_chave["260825VT599/2023"]["nao"]) == (1, 1)
    assert (por_chave["260826PL7/2026"]["sim"], por_chave["260826PL7/2026"]["abstencoes"]) == (1, 1)
    assert por_chave["260825VT599/2023"]["resultado"] == "Rejeitado"
    assert len(votos) == 4


def test_presenca_soma_meses_sem_contar_licencas():
    mes = {
        "ano": 2026,
        "mes": "fevereiro",
        "mesNumerico": 2,
        "presenca": 10,
        "licencaSaude": 4,
        "faltaJustificada": 2,
        "faltaNaoJustificada": 1,
    }
    pagina = _item(mes) + _item(
        {**mes, "mesNumerico": 3, "presenca": 9, "faltaJustificada": 0, "faltaNaoJustificada": 0}
    )
    assert alrs.presenca_da_pagina(pagina) == (22, 19)
    assert alrs.presenca_da_pagina("<html></html>") == (0, 0)


GASTOS = """
<span class="d-block d-lg-none">
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato">Impressoras - serviços de impressão local:</span><br>
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato"> - R$38,14</span>
</span>
<span class="d-block d-lg-none">
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato">Indenização por Uso de Veículo Particular em Serviço:</span><br>
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato"> - R$18.295,00</span>
</span>
<span class="d-block d-lg-none">
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato">Total:</span><br>
  <span class="responsive-value  justify-content-center" data-bs-toggle="modal" data-bs-target="#modalContrato"> - R$20.094,12</span>
</span>
"""  # fmt: skip


def test_gastos_do_mes_sem_o_total():
    gastos = alrs.gastos_da_pagina(GASTOS, 2026, 8)
    assert [(g["categoria"], str(g["valor"])) for g in gastos] == [
        ("Impressoras - serviços de impressão local", "38.14"),
        ("Indenização por Uso de Veículo Particular em Serviço", "18295.00"),
    ]
    assert alrs.gastos_da_pagina("Não foram encontradas ocorrências", 2026, 1) == []


@respx.mock
def test_coletar_junta_tudo(monkeypatch):
    monkeypatch.setattr(alrs, "PAUSA", 0)
    respx.get(alrs.DEPUTADOS).respond(json=LISTA)
    respx.get(alrs.PROPOSICOES).respond(json={"lista": PROPOSICOES})
    respx.get(f"{alrs.TRANSPARENCIA}/votos-plenario/pesquisa").respond(text=VOTOS)
    respx.get(f"{alrs.TRANSPARENCIA}/presencas-plenario/pesquisa").respond(
        text=_item({"presenca": 10, "faltaJustificada": 1, "faltaNaoJustificada": 0})
    )
    respx.get(f"{alrs.TRANSPARENCIA}/gastos/pesquisa").respond(text=GASTOS)
    casa = alrs.coletar(date(2026, 2, 15))
    assert len(casa["vereadores"]) == 2
    adao = casa["vereadores"][0]
    # 2025 + 2026 (a mesma resposta nas duas): presença soma os dois anos.
    assert (adao["sessoes"], adao["presencas"]) == (22, 20)
    assert len(adao["gastos"]) == 2 * (12 + 2)  # 12 meses de 2025 e 2 de 2026, 2 categorias
    assert len(casa["votacoes"]) == 2 and len(casa["votos"]) == 4
