"""Deputados federais em exercício (API de Dados Abertos da Câmara).

A lista não traz nome civil, telefone nem a data de início do exercício; isso vem do
detalhe de cada deputado, buscado em paralelo e guardado no mesmo arquivo bruto.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
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

    ids = [d["id"] for pagina in paginas for d in pagina["dados"]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        detalhes = pool.map(lambda i: comum.get_json(client, f"{URL}/{i}")["dados"], ids)
        return {
            "url": URL,
            "paginas": paginas,
            "detalhes": dict(zip(map(str, ids), detalhes, strict=True)),
        }


def _telefone(numero: str | None) -> str | None:
    # A Câmara publica "3215-5217"; todos os gabinetes ficam em Brasília (61).
    return f"(61) {numero}" if numero else None


def normalizar(payload: dict[str, Any]) -> list[dict[str, Any]]:
    detalhes = payload.get("detalhes", {})  # brutos antigos não têm o detalhe
    registros = []
    for pagina in payload["paginas"]:
        for d in pagina["dados"]:
            detalhe = detalhes.get(str(d["id"]), {})
            status = detalhe.get("ultimoStatus") or {}
            gabinete = status.get("gabinete") or {}
            registros.append(
                {
                    "id_externo": str(d["id"]),
                    "nome_parlamentar": d["nome"],
                    "nome_civil": comum.nome_proprio(detalhe.get("nomeCivil")),
                    "partido": d.get("siglaPartido"),
                    "uf": d["siglaUf"],
                    "foto_url": d.get("urlFoto"),
                    "email": d.get("email"),
                    "telefone": _telefone(gabinete.get("telefone")),
                    "em_exercicio_desde": (
                        date.fromisoformat(status["data"][:10]) if status.get("data") else None
                    ),
                    "pagina_url": f"https://www.camara.leg.br/deputados/{d['id']}",
                    "fonte_url": d["uri"],
                }
            )
    return registros


def executar(de_raw=None) -> int:
    return comum.executar(FONTE, CASA, URL, baixar, normalizar, de_raw=de_raw)


if __name__ == "__main__":
    comum.main(FONTE, CASA, URL, baixar, normalizar)
