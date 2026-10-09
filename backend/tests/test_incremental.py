"""Carga incremental: não baixa nem recarrega o que não mudou (comum.executar_ingestao)."""

from datetime import UTC, datetime

import httpx
import pytest
import respx
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.models import DownloadCache, FonteIngestao
from ingestion import acervo, comum

FONTE = "teste_incremental"
URL = "https://dados.exemplo.gov.br/arquivo.zip"


@pytest.fixture
def ambiente(engine, tmp_path, monkeypatch):
    """Banco de teste de verdade (a carga grava e confirma) e bruto numa pasta temporária."""
    fabrica = sessionmaker(bind=engine)
    monkeypatch.setattr(comum, "SessionLocal", fabrica)
    monkeypatch.setattr(comum, "RAW_DIR", tmp_path)
    monkeypatch.setattr(comum, "forcar", False)
    monkeypatch.setattr(comum, "cargas_sem_mudanca", 0)
    monkeypatch.setattr(comum.time, "sleep", lambda _: None)
    yield fabrica
    with fabrica() as s:
        s.execute(delete(FonteIngestao).where(FonteIngestao.fonte == FONTE))
        s.execute(delete(DownloadCache).where(DownloadCache.chave == URL))
        s.commit()


def _rodar(**kwargs) -> tuple[int, list[bytes]]:
    cargas: list[bytes] = []

    def carregar(session, payload, ingestao):
        cargas.append(payload)
        comum.conferir_carga(ingestao, [{"id": 1}, {"id": 1}], total_fonte=2, unica=("id",))
        return 2

    total = comum.executar_ingestao(
        FONTE,
        URL,
        lambda client: comum.get_bytes(client, URL),
        carregar,
        incremental=comum.Incremental(sonda=URL),
        **kwargs,
    )
    return total, cargas


def _status(fabrica) -> list[str]:
    with fabrica() as s:
        return list(
            s.scalars(
                select(FonteIngestao.status)
                .where(FonteIngestao.fonte == FONTE)
                .order_by(FonteIngestao.id)
            )
        )


def _brutos(tmp_path) -> list:
    pasta = tmp_path / FONTE
    return [a for a in pasta.glob("*") if a.is_file()] if pasta.exists() else []


@respx.mock
def test_304_nao_baixa_nem_recarrega(ambiente, tmp_path):
    head = respx.head(URL).mock(
        side_effect=[
            httpx.Response(200, headers={"ETag": '"v1"', "Content-Length": "8"}),
            httpx.Response(304),
        ]
    )
    get = respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    assert _rodar() == (2, [b"dados-v1"])
    total, cargas = _rodar()
    assert (total, cargas) == (2, [])  # devolve o total anterior: o acervo não vê queda
    assert get.call_count == 1  # só o primeiro download
    assert head.calls[1].request.headers["If-None-Match"] == '"v1"'
    assert _status(ambiente) == ["ok", "sem_mudanca"]
    assert comum.cargas_sem_mudanca == 1
    assert len(_brutos(tmp_path)) == 1


@respx.mock
def test_etag_igual_sem_304(ambiente):
    """O servidor ignora o If-None-Match e devolve 200 com o mesmo ETag."""
    respx.head(URL).mock(return_value=httpx.Response(200, headers={"ETag": '"v1"'}))
    get = respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    _rodar()
    assert _rodar()[1] == []
    assert get.call_count == 1


@respx.mock
def test_sha256_igual_nao_acumula_bruto(ambiente, tmp_path):
    """Sem validadores HTTP (HEAD recusado): baixa, vê o mesmo sha256 e descarta."""
    respx.head(URL).mock(return_value=httpx.Response(405))
    get = respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    _rodar()
    total, cargas = _rodar()
    assert (total, cargas) == (2, [])
    assert get.call_count == 2
    assert _status(ambiente) == ["ok", "sem_mudanca"]
    assert len(_brutos(tmp_path)) == 1
    with ambiente() as s:
        assert s.get(DownloadCache, URL).sha256 == comum.sha256_de(b"dados-v1")


@respx.mock
def test_arquivo_mudado_recarrega(ambiente, tmp_path):
    respx.head(URL).mock(
        side_effect=[
            httpx.Response(200, headers={"ETag": '"v1"'}),
            httpx.Response(200, headers={"ETag": '"v2"'}),
        ]
    )
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(200, content=b"dados-v1"),
            httpx.Response(200, content=b"dados-v2"),
        ]
    )
    _rodar()
    assert _rodar()[1] == [b"dados-v2"]
    assert _status(ambiente) == ["ok", "ok"]
    with ambiente() as s:
        assert s.get(DownloadCache, URL).etag == '"v2"'


@respx.mock
def test_contexto_mudou_recarrega_mesmo_igual(ambiente):
    respx.head(URL).mock(return_value=httpx.Response(304))
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    contexto = ["a"]

    def rodar():
        cargas = []
        comum.executar_ingestao(
            FONTE,
            URL,
            lambda client: comum.get_bytes(client, URL),
            lambda s, p, i: cargas.append(p) or 1,
            incremental=comum.Incremental(sonda=URL, contexto=lambda s: contexto[0]),
        )
        return cargas

    assert rodar() == [b"dados-v1"]
    assert rodar() == []
    contexto[0] = "b"  # chegaram pessoas novas, por exemplo
    assert rodar() == [b"dados-v1"]


@respx.mock
def test_forcar_ignora_o_cache(ambiente, monkeypatch):
    respx.head(URL).mock(return_value=httpx.Response(304))
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    _rodar()
    monkeypatch.setattr(comum, "forcar", True)
    assert _rodar()[1] == [b"dados-v1"]


@respx.mock
def test_carga_com_erro_nao_atualiza_o_cache(ambiente):
    respx.head(URL).mock(return_value=httpx.Response(405))
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))

    def quebra(session, payload, ingestao):
        raise RuntimeError("falhou")

    with pytest.raises(RuntimeError):
        comum.executar_ingestao(
            FONTE,
            URL,
            lambda c: comum.get_bytes(c, URL),
            quebra,
            incremental=comum.Incremental(sonda=URL),
        )
    with ambiente() as s:
        assert s.get(DownloadCache, URL) is None
    assert _rodar()[1] == [b"dados-v1"]  # a próxima tentativa carrega


@respx.mock
def test_conferencia_grava_total_e_alertas(ambiente):
    respx.head(URL).mock(return_value=httpx.Response(405))
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"dados-v1"))
    _rodar()
    with ambiente() as s:
        ingestao = s.scalars(select(FonteIngestao).where(FonteIngestao.fonte == FONTE)).one()
        assert ingestao.total_fonte == 2
        assert ingestao.alertas == ["1 linhas repetidas na chave (id)"]


def test_conferir_carga_nulos_e_total():
    ingestao = FonteIngestao(fonte="x", url="u", arquivo_raw="a")
    alertas = comum.conferir_carga(
        ingestao,
        [{"cpf": "1"}, {"cpf": None}, {"cpf": ""}],
        total_fonte=5,
        total_carregado=3,
        nao_nulos=("cpf",),
    )
    assert alertas == [
        "carregou 3 de 5 informados pela fonte",
        "campo-chave cpf vazio em 2 de 3 linhas",
    ]
    assert ingestao.total_fonte == 5
    assert comum.conferir_carga(FonteIngestao(), [{"a": 1}], unica=("a",)) == []


def test_vencidas_trata_sem_mudanca_como_sucesso(ambiente, monkeypatch):
    monkeypatch.setattr(acervo, "SessionLocal", ambiente)
    with ambiente() as s:
        s.add(
            FonteIngestao(
                fonte=FONTE,
                url=URL,
                arquivo_raw="",
                status="sem_mudanca",
                concluido_em=datetime.now(UTC),
            )
        )
        s.commit()
    assert FONTE in acervo._ultimo_ok()


def test_relatorio_mostra_total_na_fonte_e_alertas(ambiente, monkeypatch, capsys):
    monkeypatch.setattr(acervo, "SessionLocal", ambiente)
    monkeypatch.setattr(acervo, "HISTORICO", comum.RAW_DIR / "historico.json")
    agora = datetime.now(UTC)
    with ambiente() as s:
        s.add(
            FonteIngestao(
                fonte=FONTE,
                url=URL,
                arquivo_raw="x",
                status="ok",
                registros=10,
                total_fonte=12,
                alertas=["campo-chave cpf vazio em 2 de 10 linhas"],
                concluido_em=agora,
            )
        )
        s.add(
            FonteIngestao(
                fonte=FONTE,
                url=URL,
                arquivo_raw="x",
                status="sem_mudanca",
                registros=10,
                total_fonte=12,
                concluido_em=agora,
            )
        )
        s.commit()
    acervo.relatorio([acervo.Fonte(nome=FONTE, modulo="x", frequencia="diaria", uso="teste")])
    saida = capsys.readouterr().out
    linha = next(x for x in saida.splitlines() if x.startswith(FONTE))
    assert "sem_mudanca" in linha and "12" in linha
    assert "! campo-chave cpf vazio em 2 de 10 linhas" in saida


def test_rodar_com_avisos_da_carga_nao_dispara_queda(monkeypatch, capsys, tmp_path):
    """Fonte sem mudança devolve o total anterior (sem queda); os avisos da carga saem."""
    monkeypatch.setattr(acervo, "HISTORICO", tmp_path / "historico.json")
    acervo._gravar_historico({"fonte_x": 100})
    monkeypatch.setattr(acervo, "_executar", lambda fonte, hoje: 100)
    monkeypatch.setattr(acervo, "_alertas_da_carga", lambda nome, desde: ["aviso de teste"])
    fonte = acervo.Fonte(nome="fonte_x", modulo="x", frequencia="diaria", uso="teste")
    assert acervo.rodar({"fonte_x"}, [fonte]) == 0
    saida = capsys.readouterr().out
    assert "[ok]     fonte_x" in saida and "queda" not in saida
    assert "[alerta] fonte_x: aviso de teste" in saida
