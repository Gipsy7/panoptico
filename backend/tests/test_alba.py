# ruff: noqa: E501  (recortes de respostas reais da API da ALBA)
from datetime import date

import httpx
import respx

from ingestion.assembleias import alba

FREQ = [
    {"frequenciaSituacaoNome": "Presente", "frequenciaSituacaoAnos": [{"ano": 2026, "quantidade": "33"}, {"ano": 2025, "quantidade": "95"}, {"ano": 2016, "quantidade": "114"}]},
    {"frequenciaSituacaoNome": "Falta", "frequenciaSituacaoAnos": [{"ano": 2026, "quantidade": "15"}, {"ano": 2025, "quantidade": "26"}]},
    {"frequenciaSituacaoNome": "Falta Justificada", "frequenciaSituacaoAnos": [{"ano": 2026, "quantidade": "1"}]},
    {"frequenciaSituacaoNome": "Licenciado", "frequenciaSituacaoAnos": [{"ano": 2026, "quantidade": "40"}]},
]  # fmt: skip


def _parlamentar(id_, nome, razao, situacao="Ativo", legislatura="20", autor=None):
    return {"parlamentarID": id_, "parlamentarRazaoSocial": razao, "parlamentarNome": nome,
            "partidoSigla": "PSD", "parlamentarFoto": "https://x/f.jpg", "parlamentarLegislatura": legislatura,
            "parlamentarSituacao": situacao, "parlamentarTelefone": "", "parlamentarEmail": "Adolfo.Menezes@alba.ba.gov.br",
            "frequenciaPlenario": FREQ, "autorID": autor}  # fmt: skip


ADOLFO = _parlamentar(1010629, "Adolfo Menezes", "ADOLFO EMANUEL MONTEIRO DE MENEZES", autor="4288")
FELIPE = _parlamentar(1032102, "Felipe Duarte", "FELIPE GABRIEL DUARTE", autor="5020")
EX = _parlamentar(5, "Ex", "EX DEPUTADO", situacao="Inativo")
ANTIGO = _parlamentar(6, "Velho", "VELHO", legislatura="19")


def _proposicao(sigla, numero, autor, ano="2026", situacao="TRAMITANDO", id_autor=None):
    return {"sigla": sigla, "numero": numero, "ano": ano, "processo": "1908", "assunto": "Institui   o direito\r\n.",
            "data": "09/10/2026 09:51:45", "situacao": situacao, "arquivo": "https://x/a.pdf",
            "AutorRequerenteDados": {"nomeRazao": autor, "autorId": id_autor}}  # fmt: skip


def test_deputados_em_exercicio_e_frequencia():
    lista = alba.deputados({"parlamentares": [ADOLFO, FELIPE, EX, ANTIGO]})
    assert [d["parlamentarNome"] for d in lista] == ["Adolfo Menezes", "Felipe Duarte"]
    # Ano atual e anterior: presenças 33 + 95; faltas 15 + 26 + 1 justificada; licença não conta.
    assert alba.frequencia(ADOLFO, {2025, 2026}) == (170, 128)
    assert alba.frequencia({"frequenciaPlenario": []}, {2026}) == (None, None)


def test_autoria_por_nome_civil_e_por_id():
    props = [
        _proposicao("PL", "26393", "FELIPE GABRIEL DUARTE"),
        _proposicao("PL", "26394", "Nome Diferente", id_autor=4288),  # só o id do autor casa
        _proposicao("IND", "1", "ADOLFO EMANUEL MONTEIRO DE MENEZES"),
        _proposicao("PL", "9", "PODER EXECUTIVO"),  # não é de deputado
        _proposicao("OF", "3", "ADOLFO EMANUEL MONTEIRO DE MENEZES"),  # tipo que não se conta
    ]
    por = alba.distribuir(props, [ADOLFO, FELIPE])
    assert por["1032102"]["contagem"] == {"Projeto de Lei": 1}
    assert por["1010629"]["contagem"] == {"Projeto de Lei": 1, "Indicação": 1}
    projeto = por["1032102"]["projetos"][0]
    assert (projeto["id_externo"], projeto["numero"], projeto["ano"]) == (
        "PL-26393-2026",
        26393,
        2026,
    )
    assert projeto["ementa"] == "Institui o direito ."
    assert (projeto["data_apresentacao"], projeto["em_tramitacao"]) == ("2026-10-09", True)
    assert por["1010629"]["projetos"][0]["url"] == "https://x/a.pdf"
    assert len(por["1010629"]["projetos"]) == 1  # a indicação é só contagem


@respx.mock
def test_coletar_pagina_a_pagina(monkeypatch):
    monkeypatch.setattr(alba, "PAUSA", 0)
    respx.get(alba.API + "parlamentar/").respond(
        json={"total": 2, "parlamentares": [ADOLFO, FELIPE, EX]}
    )
    paginas = respx.get(alba.API + "proposicao/")
    paginas.side_effect = lambda request: httpx.Response(
        200,
        json={
            "Data": [
                _proposicao(
                    "PL",
                    str(int(request.url.params["pag"]) * 10 + int(request.url.params["ano"])),
                    "FELIPE GABRIEL DUARTE",
                    ano=request.url.params["ano"],
                )
            ],
            "Paginacao": {"atual": request.url.params["pag"], "quantidade": "2"},
        },
    )
    casa = alba.coletar(date(2026, 10, 9))
    assert paginas.call_count == 4  # 2 anos x 2 páginas
    felipe = next(v for v in casa["vereadores"] if v["id_externo"] == "1032102")
    assert len(felipe["projetos"]) == 4
    assert felipe["proposicoes_por_tipo"] == {"Projeto de Lei": 4}
    adolfo = next(v for v in casa["vereadores"] if v["id_externo"] == "1010629")
    assert (adolfo["sessoes"], adolfo["presencas"]) == (170, 128)
    assert (adolfo["email"], adolfo["nome_completo"]) == (
        "adolfo.menezes@alba.ba.gov.br",
        "Adolfo Emanuel Monteiro de Menezes",
    )
    assert len(casa["vereadores"]) == 2  # o inativo fica de fora
