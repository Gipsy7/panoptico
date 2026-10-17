"""Resiliência da ingestão: retry do HTTP, votações do Senado e segunda passada do run_all."""

import time

import httpx
import pytest

from ingestion import comum, run_all
from ingestion.receita import socios
from ingestion.senado import votacoes


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    esperas = []
    monkeypatch.setattr(comum.time, "sleep", esperas.append)
    return esperas


def _cliente(servidor):
    return httpx.Client(transport=httpx.MockTransport(servidor))


def test_retry_recupera_depois_de_503_e_connect_timeout(sem_espera):
    respostas = iter([503, "timeout", 503, 200])

    def servidor(request):
        r = next(respostas)
        if r == "timeout":
            raise httpx.ConnectTimeout("lento", request=request)
        return httpx.Response(r, json={"ok": True})

    with _cliente(servidor) as client:
        assert comum.get_json(client, "https://x/a") == {"ok": True}
    assert len(sem_espera) == 3
    assert all(0 < e <= comum.TETO_ESPERA + 1 for e in sem_espera)


def test_retry_trata_read_timeout_e_protocolo(sem_espera):
    erros = iter([httpx.ReadTimeout("x"), httpx.RemoteProtocolError("x")])

    def servidor(request):
        try:
            raise next(erros)
        except StopIteration:
            return httpx.Response(200, json=[1])

    with _cliente(servidor) as client:
        assert comum.get_json(client, "https://x/a") == [1]


def test_404_nao_tenta_de_novo(sem_espera):
    pedidos = []

    def servidor(request):
        pedidos.append(1)
        return httpx.Response(404)

    with _cliente(servidor) as client, pytest.raises(httpx.HTTPStatusError):
        comum.get_json(client, "https://x/a")
    assert len(pedidos) == 1 and sem_espera == []


def test_desiste_depois_de_5_tentativas_e_respeita_tentativas_explicitas():
    pedidos = []

    def servidor(request):
        pedidos.append(1)
        return httpx.Response(503)

    with _cliente(servidor) as client:
        with pytest.raises(httpx.HTTPStatusError):
            comum.get_json(client, "https://x/a")
        assert len(pedidos) == 5
        pedidos.clear()
        with pytest.raises(httpx.HTTPStatusError):
            comum.get_json(client, "https://x/a", tentativas=2)
        assert len(pedidos) == 2


def test_retry_after_e_teto(sem_espera):
    respostas = iter([httpx.Response(429, headers={"Retry-After": "500"}), httpx.Response(200)])
    with _cliente(lambda r: next(respostas)) as client:
        comum.get_bytes(client, "https://x/a")
    assert sem_espera == [60]


def test_votacao_pula_data_com_orientacao_fora_do_ar(sem_espera, capsys):
    def servidor(request):
        url = str(request.url)
        if "orientacaoBancada/20250429" in url:
            return httpx.Response(503)
        if "orientacaoBancada" in url:
            return httpx.Response(200, json={"votacoes": []})
        return httpx.Response(
            200,
            json=[
                {"dataSessao": "2025-04-29T10:00", "votos": [{}]},
                {"dataSessao": "2025-04-30T10:00", "votos": [{}]},
            ],
        )

    with _cliente(servidor) as client:
        payload = votacoes.baixar(client, 2025)
    assert list(payload["orientacoes"]) == ["2025-04-30"]
    assert len(payload["votacoes"]) == 2
    assert "2025-04-29" in capsys.readouterr().out


def _tarefas(monkeypatch, tarefas):
    monkeypatch.setattr(run_all, "_tarefas", lambda: tarefas)
    monkeypatch.setattr(run_all.limpar_raw, "limpar", lambda: [])
    monkeypatch.setattr(run_all.time, "sleep", lambda _: None)


def test_run_all_falha_uma_vez_termina_com_exit_0(monkeypatch, tmp_path):
    chamadas = {"a": 0}

    def instavel():
        chamadas["a"] += 1
        if chamadas["a"] == 1:
            raise RuntimeError("timeout")
        return 7

    resumo = tmp_path / "resumo.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(resumo))
    monkeypatch.setenv("INGESTAO_ESPERA_SEGUNDA_PASSADA", "0")
    _tarefas(monkeypatch, [("ibge", instavel), ("outra", lambda: 1)])
    assert run_all.main() == 0
    assert chamadas["a"] == 2
    texto = resumo.read_text(encoding="utf-8")
    assert "ibge" in texto and "Recuperadas" in texto


def test_run_all_falha_sempre_termina_com_exit_1(monkeypatch):
    def quebrada():
        raise RuntimeError("503")

    monkeypatch.setenv("INGESTAO_ESPERA_SEGUNDA_PASSADA", "0")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _tarefas(monkeypatch, [("votacoes", quebrada), ("outra", lambda: 1)])
    assert run_all.main() == 1


def test_socios_prazo_vale_dentro_da_consulta(monkeypatch):
    dormidas = []
    monkeypatch.setattr(socios.time, "sleep", dormidas.append)
    pedidos = []

    def servidor(request):
        pedidos.append(1)
        return httpx.Response(503)

    limite = time.monotonic() + 5
    with _cliente(servidor) as client:
        assert socios.consultar(client, "12345678000199", limite) is None
    assert all(d <= 5 for d in dormidas)  # nenhuma espera passa do que resta do prazo
    with _cliente(servidor) as client:
        pedidos.clear()
        assert socios.consultar(client, "12345678000199", time.monotonic() - 1) is None
    assert pedidos == []  # prazo vencido: nem tenta
