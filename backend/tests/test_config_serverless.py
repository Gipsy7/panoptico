import importlib

import pytest

import app.config as cfg


@pytest.mark.parametrize(
    ("vercel", "serverless", "esperado"),
    [(None, None, False), ("1", None, True), (None, "1", True), ("0", "0", False)],
)
def test_serverless_por_ambiente(monkeypatch, vercel, serverless, esperado):
    for nome, valor in (("VERCEL", vercel), ("SERVERLESS", serverless)):
        if valor is None:
            monkeypatch.delenv(nome, raising=False)
        else:
            monkeypatch.setenv(nome, valor)
    importlib.reload(cfg)
    try:
        assert cfg.Settings().serverless is esperado
    finally:
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.delenv("SERVERLESS", raising=False)
        importlib.reload(cfg)
