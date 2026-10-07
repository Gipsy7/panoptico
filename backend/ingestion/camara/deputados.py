"""Deputados federais em exercício (API de Dados Abertos da Câmara)."""

from typing import Any

import httpx

from ingestion import comum

FONTE = "camara_deputados"
CASA = "camara"
URL = "https://dadosabertos.camara.leg.br/api/v2/deputados"


def baixar(client: httpx.Client) -> dict[str, Any]:
    paginas = []
    url: str | None = URL
    params: dict | None = {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"}
    while url:
        pagina = comum.get_json(client, url, params=params)
        paginas.append(pagina)
        url = next((link["href"] for link in pagina["links"] if link["rel"] == "next"), None)
        params = None  # o link "next" já traz os parâmetros
    return {"url": URL, "paginas": paginas}


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    registros = []
    for pagina in payload["paginas"]:
        for d in pagina["dados"]:
            registros.append(
                {
                    "id_externo": str(d["id"]),
                    "nome_parlamentar": d["nome"],
                    "nome_civil": None,
                    "partido": d.get("siglaPartido"),
                    "uf": d["siglaUf"],
                    "foto_url": d.get("urlFoto"),
                    "email": d.get("email"),
                    "telefone": None,
                    "pagina_url": f"https://www.camara.leg.br/deputados/{d['id']}",
                    "fonte_url": d["uri"],
                }
            )
    return registros


def executar(de_raw=None) -> int:
    return comum.executar(FONTE, CASA, URL, baixar, normalizar, de_raw=de_raw)


if __name__ == "__main__":
    comum.main(FONTE, CASA, URL, baixar, normalizar)
