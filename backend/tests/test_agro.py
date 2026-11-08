"""PAM do IBGE: valores reais de Blumenau em 2025 (API v3 do SIDRA, 08/11/2026)."""

from decimal import Decimal

import pytest
from sqlalchemy import insert

from app.models import AgroLavoura, AgroPecuaria, Municipio
from ingestion.ibge import pam
from tests.test_api import _ingestao


def _recorte(valores: dict) -> dict:
    return {"ano": 2025, "valores": valores}


def test_normalizar_tira_zeros_sem_dado_e_asterisco():
    rec = _recorte(
        {
            "Total": {"4202404": "4500", "1": "4500"},
            "Palmito": {"4202404": "2400"},
            "Abacaxi*": {"4202404": "-"},
            "Soja (em grão)": {"4202404": "..."},
            "Banana (cacho)": {"4202404": "1589", "1": "1589"},
        }
    )
    linhas = {(r["codigo"], r["produto"]): r["valor"] for r in pam.normalizar(rec)}
    assert linhas[("4202404", "Palmito")] == Decimal(2400)
    assert ("4202404", "Abacaxi") not in linhas and ("4202404", "Soja (em grão)") not in linhas
    pam.conferir(pam.normalizar(rec))


def test_conferir_e_minimo_de_municipios(session):
    with pytest.raises(ValueError):
        pam.conferir(pam.normalizar(_recorte({"Total": {"4202404": "10", "1": "100"}})))
    with pytest.raises(ValueError):
        pam.carregar(session, _recorte({"Total": {"4202404": "1", "1": "1"}}), _ingestao(session))


def test_rota_do_agro(client, session):
    session.add(Municipio(ibge="4202404", nome="Blumenau", uf="SC", nome_chave="BLUMENAU"))
    session.flush()
    linhas = [("4202404", "Total", 4500), ("4202404", "Palmito", 2400),
              ("4202404", "Banana (cacho)", 1589), ("4202404", "Milho (em grão)", 348),
              ("42", "Total", 20000000)]  # fmt: skip
    session.execute(
        insert(AgroLavoura),
        [{"codigo": c, "ano": 2025, "produto": p, "valor": v} for c, p, v in linhas],
    )
    corpo = client.get("/municipios/4202404/agro").json()
    assert corpo["ano"] == 2025 and corpo["valor_total"] == 4_500_000
    assert [p["produto"] for p in corpo["produtos"]] == [
        "Palmito",
        "Banana (cacho)",
        "Milho (em grão)",
    ]
    assert round(corpo["produtos"][0]["percentual"], 1) == round(100 * 2400 / 4500, 1)
    assert corpo["uf_valor_total"] == 20_000_000_000
    assert corpo["pecuaria"] is None
    session.execute(
        insert(AgroPecuaria),
        [{"codigo": "4202404", "ano": 2025, "categoria": c, "item": i, "valor": v}
         for c, i, v in [("rebanho", "Bovino", 6824), ("rebanho", "Galináceos - total", 721789),
                         ("produto", "Total", 118568), ("produto", "Ovos de galinha", 111662),
                         ("produto", "Leite", 6720)]],
    )  # fmt: skip
    pec = client.get("/municipios/4202404/agro").json()["pecuaria"]
    assert [r["item"] for r in pec["rebanhos"]] == ["Galináceos", "Bovino"]
    assert pec["valor_origem_animal"] == 118_568_000
    assert pec["produtos"][0]["produto"] == "Ovos de galinha"
    assert client.get("/municipios/9999999/agro").status_code == 404
