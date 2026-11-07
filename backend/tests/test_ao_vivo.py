"""O Plenário agora: sessão em andamento, próxima sessão e falha da fonte.

Respostas no formato real das APIs (Câmara /eventos e /eventos/{id}/pauta; Senado
/plenario/agenda/mes), servidas por MockTransport: sem rede.
"""

from datetime import datetime

import httpx
import pytest

from app.services import ao_vivo as s

AGORA = datetime(2026, 11, 10, 15, 42, tzinfo=s.BRASILIA)

CAMARA_EM_ANDAMENTO = {
    "dados": [
        {
            "id": 83100,
            "dataHoraInicio": "2026-11-10T14:06",
            "dataHoraFim": None,
            "situacao": "Em Andamento",
            "descricaoTipo": "Sessão Deliberativa",
            "descricao": "Sessão Deliberativa Extraordinária",
            "urlRegistro": "https://www.youtube.com/watch?v=abc",
        },
        {
            "id": 83101,
            "dataHoraInicio": "2026-11-10T09:00",
            "situacao": "Encerrada",
            "descricaoTipo": "Reunião de Comissão",
            "urlRegistro": None,
        },
    ]
}
CAMARA_PAUTA = {
    "dados": [
        {
            "ordem": 1,
            "titulo": "PL 5649/2026",
            "proposicao_": {"id": 1, "ementa": "Autoriza   o apoio\nfinanceiro a produtores."},
            "proposicaoRelacionada_": None,
        },
        # O item se repete uma vez por votação (mesma ordem): entra uma vez só.
        {"ordem": 1, "titulo": "PL 5649/2026", "proposicao_": {"id": 1, "ementa": "x"}},
        {
            "ordem": 2,
            "titulo": "",
            "proposicao_": {"id": 2, "siglaTipo": "PL", "numero": 68, "ano": 2025},
        },
    ]
}
CAMARA_AGENDADAS = {
    "dados": [
        {
            "id": 83110,
            "dataHoraInicio": "2026-11-10T09:00",
            "situacao": "Encerrada",
            "descricaoTipo": "Sessão Não Deliberativa",
        },
        {
            "id": 83111,
            "dataHoraInicio": "2026-11-11T13:55",
            "situacao": "Cancelada",
            "descricaoTipo": "Sessão Deliberativa",
        },
        {
            "id": 83112,
            "dataHoraInicio": "2026-11-12T13:55",
            "situacao": "Agendada",
            "descricaoTipo": "Sessão Deliberativa",
        },
    ]
}


def _sessao_senado(codigo, data, hora, tipo, situacao, materias=None):
    sessao = {
        "Data": data,
        "Hora": hora,
        "TipoSessao": tipo,
        "CodigoSessao": codigo,
        "SituacaoSessao": situacao,
    }
    if materias is not None:
        sessao["Materias"] = {"Materia": materias}
    return sessao


def _agenda(*sessoes):
    return {"AgendaPlenario": {"Sessoes": {"Sessao": list(sessoes)}}}


MATERIA = {
    "CodigoMateria": "176119",
    "DescricaoIdentificacaoMateria": "RQS 729/2026",
    "EmentaPapeleta": "solicita Sessão Especial para celebrar o Dia do Síndico.",
}


def _fabrica(camara, senado, pauta=None, chamadas=None):
    def tratar(request: httpx.Request) -> httpx.Response:
        if chamadas is not None:
            chamadas.append(str(request.url))
        url = request.url.host + request.url.path
        if url.endswith("/eventos") and "camara" in url:
            if isinstance(camara, Exception):
                raise camara
            return httpx.Response(200, json=camara)
        if "/pauta" in url:
            return httpx.Response(200, json=pauta or {"dados": []})
        if "senado" in url:
            if isinstance(senado, Exception):
                raise senado
            return httpx.Response(200, json=senado)
        return httpx.Response(404)

    return lambda: httpx.Client(transport=httpx.MockTransport(tratar))


@pytest.fixture(autouse=True)
def _sem_cache():
    s.limpar_cache()
    yield
    s.limpar_cache()


def _casa(resultado, nome):
    return next(c for c in resultado["casas"] if c["casa"] == nome)


def test_camara_em_andamento_traz_itens_e_video():
    senado = _agenda(
        _sessao_senado("1", "2026-11-11", "14:00", "SESSÃO DELIBERATIVA ORDINÁRIA ", "Agendada")
    )
    r = s.ao_vivo(_fabrica(CAMARA_EM_ANDAMENTO, senado, CAMARA_PAUTA), AGORA)
    c = _casa(r, "camara")
    assert c["situacao"] == "agora"
    assert c["titulo"] == "Sessão Deliberativa"
    assert c["inicio"] == "2026-11-10T14:06"
    assert c["url_video"] == "https://www.youtube.com/watch?v=abc"
    assert c["total_itens"] == 2
    assert c["itens"][0] == {
        "rotulo": "PL 5649/2026",
        "descricao": "Autoriza o apoio financeiro a produtores.",
    }
    assert c["itens"][1]["rotulo"] == "PL 68/2025"
    assert r["conferido_em"] == "2026-11-10T18:42:00+00:00"
    assert r["fonte_url"].startswith("https://")


def test_camara_sem_registro_de_video_aponta_a_pagina_do_evento():
    sem_url = {"dados": [{**CAMARA_EM_ANDAMENTO["dados"][0], "urlRegistro": None}]}
    r = s.ao_vivo(_fabrica(sem_url, _agenda()), AGORA)
    assert _casa(r, "camara")["url_video"] == "https://www.camara.leg.br/evento-legislativo/83100"


def test_proxima_sessao_ignora_encerrada_e_cancelada():
    r = s.ao_vivo(_fabrica(CAMARA_AGENDADAS, _agenda()), AGORA)
    c = _casa(r, "camara")
    assert c["situacao"] == "proxima"
    assert c["proxima"] == {"inicio": "2026-11-12T13:55", "titulo": "Sessão Deliberativa"}
    assert c["url_video"] is None
    assert _casa(r, "senado")["situacao"] == "sem"


def test_senado_em_andamento_e_proxima_sessao():
    agenda = _agenda(
        _sessao_senado(
            "1", "2026-11-10", "14:00", "SESSÃO DELIBERATIVA ORDINÁRIA ", "Em andamento", [MATERIA]
        ),
        _sessao_senado("2", "2026-11-11", "14:00", "SESSÃO ESPECIAL ", "Agendada"),
    )
    r = s.ao_vivo(_fabrica({"dados": []}, agenda), AGORA)
    c = _casa(r, "senado")
    assert c["situacao"] == "agora"
    assert c["titulo"] == "Sessão deliberativa ordinária"
    assert c["itens"] == [
        {
            "rotulo": "RQS 729/2026",
            "descricao": "solicita Sessão Especial para celebrar o Dia do Síndico.",
        }
    ]
    assert c["url_video"].startswith("https://www12.senado.leg.br/tv")
    assert _casa(r, "camara")["situacao"] == "sem"

    s.limpar_cache()
    so_futura = _agenda(
        _sessao_senado("1", "2026-11-10", "10:00", "SESSÃO ESPECIAL ", "Encerrada"),
        _sessao_senado("2", "2026-11-13", "10:00", "SESSÃO NÃO DELIBERATIVA ", "Agendada"),
        _sessao_senado("3", "2026-11-11", "14:00", "SESSÃO SOLENE ", "Convocada"),
    )
    c = _casa(s.ao_vivo(_fabrica({"dados": []}, so_futura), AGORA), "senado")
    assert c["situacao"] == "proxima"
    assert c["proxima"] == {"inicio": "2026-11-11T14:00", "titulo": "Sessão solene"}


def test_senado_com_uma_sessao_so_vem_como_objeto():
    agenda = {
        "AgendaPlenario": {
            "Sessoes": {
                "Sessao": _sessao_senado("2", "2026-11-11", "14:00", "SESSÃO ESPECIAL ", "Agendada")
            }
        }
    }
    c = _casa(s.ao_vivo(_fabrica({"dados": []}, agenda), AGORA), "senado")
    assert c["situacao"] == "proxima"


def test_cache_evita_nova_consulta_dentro_do_prazo():
    chamadas: list[str] = []
    fabrica = _fabrica({"dados": []}, _agenda(), chamadas=chamadas)
    s.ao_vivo(fabrica, AGORA)
    primeiras = len(chamadas)
    assert primeiras >= 2
    s.ao_vivo(fabrica, AGORA)
    assert len(chamadas) == primeiras


def test_fonte_fora_usa_a_ultima_resposta_boa(monkeypatch):
    s.ao_vivo(_fabrica(CAMARA_EM_ANDAMENTO, _agenda(), CAMARA_PAUTA), AGORA)
    # Cache vencido e fonte fora do ar: vale a resposta anterior, com a hora dela.
    monkeypatch.setattr(s, "TTL_SEGUNDOS", -1)
    erro = httpx.ConnectError("sem rede")
    depois = datetime(2026, 11, 10, 16, 0, tzinfo=s.BRASILIA)
    r = s.ao_vivo(_fabrica(erro, erro), depois)
    c = _casa(r, "camara")
    assert c["situacao"] == "agora"
    assert c["conferido_em"] == "2026-11-10T18:42:00+00:00"
    assert not c["indisponivel"]


def test_fonte_fora_sem_resposta_anterior_diz_sem_sessao_e_indisponivel():
    erro = httpx.ConnectError("sem rede")
    r = s.ao_vivo(_fabrica(erro, erro), AGORA)
    for c in r["casas"]:
        assert c["situacao"] == "sem"
        assert c["indisponivel"] is True
        assert c["conferido_em"] is None
    assert r["conferido_em"] is None


def test_rota_responde_com_cache_curto(client, monkeypatch):
    monkeypatch.setattr(s, "_cliente", _fabrica({"dados": []}, _agenda()))
    monkeypatch.setattr(s, "ao_vivo", lambda: {"conferido_em": None, "casas": []})
    resp = client.get("/ao-vivo")
    assert resp.status_code == 200
    assert resp.headers["cache-control"].startswith("public, max-age=60")
