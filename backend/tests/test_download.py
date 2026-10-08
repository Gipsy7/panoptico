import httpx

from ingestion import comum

CONTEUDO = bytes(range(256)) * 40


class _Cortado(httpx.SyncByteStream):
    """Entrega metade e derruba a conexão, como o servidor do TCE-SP."""

    def __iter__(self):
        yield CONTEUDO[: len(CONTEUDO) // 2]
        raise httpx.RemoteProtocolError("peer closed connection")


def test_download_retoma_com_range(monkeypatch):
    monkeypatch.setattr(comum.time, "sleep", lambda _: None)
    pedidos = []

    def servidor(request: httpx.Request) -> httpx.Response:
        faixa = request.headers.get("Range")
        pedidos.append(faixa)
        if faixa is None:
            return httpx.Response(200, stream=_Cortado())
        inicio = int(faixa.removeprefix("bytes=").rstrip("-"))
        return httpx.Response(206, content=CONTEUDO[inicio:])

    with httpx.Client(transport=httpx.MockTransport(servidor)) as client:
        arquivo = comum.baixar_para_arquivo(client, "https://x/arquivo.zip")
    assert arquivo.read_bytes() == CONTEUDO
    assert pedidos == [None, f"bytes={len(CONTEUDO) // 2}-"]
    arquivo.unlink()
