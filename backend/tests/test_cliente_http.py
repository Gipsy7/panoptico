"""O cliente HTTP das ingestões liga só por IPv4 (runners do GitHub não têm rota IPv6)."""

from ingestion import comum


def test_cliente_liga_so_por_ipv4():
    with comum.criar_cliente() as client:
        pool = client._transport._pool
        assert pool._local_address == "0.0.0.0"
