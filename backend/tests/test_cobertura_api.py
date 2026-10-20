import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import cobertura

client = TestClient(app)


def test_sem_uf_traz_nacional_e_lista_de_ufs():
    r = client.get("/cobertura")
    assert r.status_code == 200
    d = r.json()
    assert len(d["ufs"]) == 27
    n = d["nacional"]
    assert n["total"] == sum(n[s] for s in cobertura.SITUACOES) > 0
    assert d["casas"] == [] and d["uf"] is None


def test_uf_traz_casas_e_pedidos():
    d = client.get("/cobertura", params={"uf": "pr"}).json()
    assert d["uf"] == "PR"
    assert d["resumo_uf"]["total"] == sum(len(c["secoes"]) for c in d["casas"])
    pedidos = [p for c in d["casas"] for s in c["secoes"] for p in s["pedidos"]]
    assert any(p["url"].startswith("https://") for p in pedidos)


def test_uf_inexistente_da_404():
    assert client.get("/cobertura", params={"uf": "XX"}).status_code == 404


def test_json_empacotado_igual_ao_csv():
    """Se falhar: python -m app.services.cobertura (regenera a partir do CSV)."""
    atual = json.loads(cobertura.JSON.read_text(encoding="utf-8"))["linhas"]
    assert atual == cobertura.gerar()["linhas"]
