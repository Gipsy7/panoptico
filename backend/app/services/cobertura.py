"""Régua pública de cobertura: o que o site mostra (ou não) de cada cargo, em cada Estado.

Lê `backend/app/dados/cobertura.json`, empacotado com a API (a pasta `data/` da raiz não vai
para a Vercel). O JSON é gerado a partir de `data/cobertura_matriz.csv` (que sai de
`ingestion.cobertura`) e de `docs/pedidos/README.md`:

    python -m app.services.cobertura
"""

import csv
import json
import re
from datetime import date
from pathlib import Path

JSON = Path(__file__).resolve().parents[1] / "dados" / "cobertura.json"
RAIZ = Path(__file__).resolve().parents[3]
CSV_MATRIZ = RAIZ / "data" / "cobertura_matriz.csv"
README_PEDIDOS = RAIZ / "docs" / "pedidos" / "README.md"
URL_PEDIDOS = "https://github.com/Gipsy7/panoptico/blob/main/docs/pedidos/"
URL_MATRIZ = "https://github.com/Gipsy7/panoptico/blob/main/data/cobertura_matriz.csv"
SITUACOES = ["sim", "parcial", "bloqueado", "pedido", "sem_fonte"]
NACIONAL = "BR"  # Câmara dos Deputados e Senado: valem para todos os estados


def _pedidos_do_readme() -> dict[str, dict]:
    """arquivo.md -> {orgao, data (dd/mm) ou None, url}."""
    pedidos: dict[str, dict] = {}
    for linha in README_PEDIDOS.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("|"):
            continue
        colunas = [c.strip() for c in linha.strip("|").split("|")]
        achado = re.search(r"\[([^\]]+\.md)\]", colunas[-1]) if len(colunas) >= 4 else None
        if not achado:
            continue
        data = re.search(r"(\d{2}/\d{2})/\d{4}", colunas[2])
        pedidos[achado.group(1)] = {
            "arquivo": achado.group(1),
            "orgao": colunas[0],
            "data": data.group(1) if data else None,
            "url": URL_PEDIDOS + achado.group(1),
        }
    return pedidos


def gerar() -> dict:
    with CSV_MATRIZ.open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    pedidos = _pedidos_do_readme()
    saida = []
    for r in linhas:
        arquivos = [a.strip() for a in r["pedido"].split(";") if a.strip()]
        saida.append(
            {
                "uf": r["uf"],
                "casa": r["casa"],
                "cargo": r["cargo"],
                "secao": r["secao"],
                "situacao": r["situacao"],
                "motivo": r["motivo"],
                "fonte": r["fonte"],
                "pedidos": [pedidos[a] for a in arquivos if a in pedidos],
            }
        )
    return {"gerado_em": date.today().isoformat(), "linhas": saida}


def _carregar() -> dict:
    return json.loads(JSON.read_text(encoding="utf-8"))


def _contar(linhas: list[dict]) -> dict:
    contagem = {s: 0 for s in SITUACOES}
    for r in linhas:
        contagem[r["situacao"]] += 1
    contagem["total"] = len(linhas)
    return contagem


def cobertura(uf: str | None) -> dict | None:
    """None quando a UF não existe na matriz."""
    dados = _carregar()
    linhas = dados["linhas"]
    resposta = {
        "ufs": sorted({r["uf"] for r in linhas} - {NACIONAL}),
        "uf": None,
        "nacional": _contar(linhas),
        "resumo_uf": None,
        "casas": [],
        "fonte_nome": "Matriz de cobertura do Panóptico",
        "fonte_url": URL_MATRIZ,
        "atualizado_em": dados["gerado_em"],
    }
    if uf is None:
        return resposta
    uf = uf.upper()
    da_uf = [r for r in linhas if r["uf"] in (uf, NACIONAL)]
    if uf == NACIONAL or uf not in resposta["ufs"]:
        return None
    casas: dict[tuple[str, str], list[dict]] = {}
    for r in da_uf:
        casas.setdefault((r["casa"], r["cargo"]), []).append(
            {k: r[k] for k in ("secao", "situacao", "motivo", "fonte", "pedidos")}
        )
    resposta["uf"] = uf
    resposta["resumo_uf"] = _contar(da_uf)
    resposta["casas"] = [
        {"casa": casa, "cargo": cargo, "secoes": secoes} for (casa, cargo), secoes in casas.items()
    ]
    return resposta


if __name__ == "__main__":
    JSON.parent.mkdir(exist_ok=True)
    JSON.write_text(
        json.dumps(gerar(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"Gravado {JSON}")
