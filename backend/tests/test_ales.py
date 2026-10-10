# ruff: noqa: E501  (recortes de respostas reais da API da ALES)
from datetime import date

import httpx
import respx

from ingestion.assembleias import ales, ple


def _freq(presente, ausencia, justificada, licenciado):
    def grupo(nome, qtd):
        return {"frequenciaSituacaoNome": nome, "frequenciaSituacaoAnos": [{"ano": 2026, "quantidade": str(qtd)}, {"ano": 2025, "quantidade": "0"}, {"ano": 2019, "quantidade": "99"}]}  # fmt: skip

    return [grupo("Presente", presente), grupo("Ausência", ausencia), grupo("Ausência Justificada", justificada), grupo("Falta", 0), grupo("Licenciado", licenciado)]  # fmt: skip


def _parlamentar(id_, nome, razao, situacao, autor):
    return {"parlamentarID": str(id_), "parlamentarRazaoSocial": razao, "parlamentarNome": nome,
            "partidoSigla": "PP", "parlamentarFoto": "https://www3.al.es.gov.br/Arquivo/images/pessoas/x.jpg",
            "parlamentarLegislatura": "20", "parlamentarSituacao": situacao, "parlamentarTelefone": "",
            "parlamentarEmail": "dep.adilsonespindula@al.es.gov.br", "autorID": autor,
            "frequenciaPlenario": _freq(128, 1, 2, 40)}  # fmt: skip


ADILSON = _parlamentar(40, "ADILSON ESPINDULA", "Adilson Espíndula", "Ativos", "1376")
JOSE = _parlamentar(41, "ENGENHEIRO JOSE ESMERALDO", "Engenheiro José Esmeraldo", "Ativos", "29")
SUPLENTE = _parlamentar(
    99, "BRUNO LAMAS", "Bruno Lamas", "Deputados Suplentes participantes da Legislatura", "5"
)
TITULAR_FORA = _parlamentar(
    98,
    "LUCAS SCARAMUSSA",
    "Lucas Scaramussa",
    "Deputados Titulares que não encerraram o mandato",
    "6",
)


def _prop(sigla, numero, autor, id_autor, situacao="Tramitando", ano="2026"):
    return {"sigla": sigla, "numero": numero, "ano": ano, "processo": "21006", "assunto": "Revoga a Lei nº 11.935,\r\n  que declara.",
            "data": "08/10/2026 17:29:20", "situacao": situacao,
            "arquivo": "https://www3.al.es.gov.br/Arquivo/Documents/2026/10/08/PL/496857.pdf",
            "AutorRequerenteDados": {"nomeRazao": autor, "autorId": id_autor}}  # fmt: skip


def test_so_os_ativos_e_frequencia_com_ausencias():
    lista = ple.deputados({"parlamentares": [ADILSON, JOSE, SUPLENTE, TITULAR_FORA]})
    assert [d["parlamentarNome"] for d in lista] == [
        "ADILSON ESPINDULA",
        "ENGENHEIRO JOSE ESMERALDO",
    ]
    # Ano atual e anterior (2019 fica de fora): 128 presenças; ausência e ausência justificada são faltas; licença não conta.
    assert ple.frequencia(ADILSON, {2025, 2026}) == (131, 128)


@respx.mock
def test_coletar_pede_so_os_tipos_que_interessam(monkeypatch):
    monkeypatch.setattr(ales, "PAUSA", 0)
    respx.get(ales.API + "parlamentar/").respond(
        json={"total": 4, "parlamentares": [ADILSON, JOSE, SUPLENTE, TITULAR_FORA], "paginacao": {}}
    )
    chamadas = []

    def proposicoes(request):
        sigla = request.url.params["sigla"]
        chamadas.append((sigla, request.url.params["ano"]))
        itens = {
            "PL": [
                _prop(
                    "PL", "529", "Engenherio José Esmeraldo", "29"
                ),  # nome com erro de digitação: casa pelo id do autor
                _prop("PL", "525", "GOVERNADOR DO ESTADO", "972"),  # do Executivo: fora
            ],
            "IND": [_prop("IND", "1585", "Adilson Espíndula", "1376")],
        }.get(sigla, [])
        return httpx.Response(
            200, json={"Data": itens, "Paginacao": {"atual": "1", "quantidade": "1"}}
        )

    respx.get(ales.API + "proposicao/").side_effect = proposicoes
    casa = ales.coletar(date(2026, 10, 9))
    assert len(chamadas) == 2 * (
        len(ales.PROJETOS) + len(ales.CONTAGEM)
    )  # uma página por tipo e ano
    assert ("PL", "2025") in chamadas and ("IND", "2026") in chamadas
    assert [v["nome"] for v in casa["vereadores"]] == [
        "Adilson Espindula",
        "Engenheiro Jose Esmeraldo",
    ]
    jose = casa["vereadores"][1]
    assert len(jose["projetos"]) == 2  # PL 529 nos dois anos pedidos
    assert jose["projetos"][0]["id_externo"] == "PL-529-2026"
    assert jose["projetos"][0]["ementa"] == "Revoga a Lei nº 11.935, que declara."
    assert jose["projetos"][0]["em_tramitacao"] is True
    adilson = casa["vereadores"][0]
    assert adilson["proposicoes_por_tipo"] == {"Indicação": 2}
    assert (adilson["sessoes"], adilson["presencas"]) == (131, 128)
    assert adilson["email"] == "dep.adilsonespindula@al.es.gov.br"
