"""Nomes de gastos que a fonte grafa diferente do deputado (apelido, erro de digitação,
abreviação). Vale para qualquer assembleia ou câmara cuja planilha de gastos traga só o nome.

Regra: só o nome idêntico (após `comum.chave_nome`) liga sozinho (`base.ligar_nomes_exatos`).
O resto vira sugestão, gravada em `data/processed/apelidos_pendentes_<escopo>.csv` (fora do
git, só para o revisor; nada dali chega à API, ao site ou à exportação). Quem decide é uma
pessoa, em `python -m ingestion.revisar --tipo apelido`; a decisão vai para
`data/curadoria/apelidos_revisados.csv` (versionado) e é reaplicada a cada carga, também na VPS.

O deputado é identificado pelo `id_externo` da Casa (estável), não pelo nome.
"""

import csv
import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path

from app.config import BACKEND_DIR
from ingestion import comum
from ingestion.identidade import _palavras

REVISADOS = BACKEND_DIR.parent / "data" / "curadoria" / "apelidos_revisados.csv"
PENDENTES_DIR = BACKEND_DIR / "data" / "processed"
COLUNAS = [
    "escopo",
    "nome_fonte",
    "id_externo",
    "nome_deputado",
    "decisao",
    "revisado_por",
    "revisado_em",
    "observacao",
]
COLUNAS_PENDENTES = ["escopo", "nome_fonte", "linhas", "valor", "candidatos"]
LIMIAR = 0.62
MAX_CANDIDATOS = 3


def _id(d: dict) -> str:
    """Identificador estável do deputado na lista da Casa (`id_externo`, `id` ou `slug`)."""
    return str(d.get("id_externo") or d.get("id") or d.get("slug") or "")


def pendentes_caminho(escopo: str) -> Path:
    return PENDENTES_DIR / f"apelidos_pendentes_{escopo}.csv"


def decisoes(escopo: str | None = None, caminho: Path | None = None) -> list[dict[str, str]]:
    caminho = caminho or REVISADOS
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            {k: (v or "").strip() for k, v in linha.items()}
            for linha in csv.DictReader(arquivo)
            if (linha.get("decisao") or "").strip() in ("aceito", "recusado")
            and (escopo is None or linha.get("escopo") == escopo)
        ]


def pontuacao(nome_fonte: str, nome_deputado: str) -> float:
    """Semelhança de 0 a 1 entre dois nomes: a maior entre a razão de caracteres e a das
    palavras sem partículas e títulos."""
    a, b = comum.chave_nome(nome_fonte), comum.chave_nome(nome_deputado)
    if not a or not b:
        return 0.0
    letras = SequenceMatcher(None, a, b).ratio()
    pa, pb = " ".join(_palavras(a)), " ".join(_palavras(b))
    palavras = SequenceMatcher(None, pa, pb).ratio() if pa and pb else 0.0
    return max(letras, palavras)


def sugerir(nome_fonte: str, deputados: list[dict]) -> list[dict]:
    """Até três deputados parecidos, do mais ao menos parecido. Só sugestão."""
    achados = sorted(
        (
            {
                "id_externo": _id(d),
                "nome": d["nome"],
                "pontuacao": round(pontuacao(nome_fonte, d["nome"]), 2),
            }
            for d in deputados
        ),
        key=lambda c: -c["pontuacao"],
    )
    return [c for c in achados if c["pontuacao"] >= LIMIAR][:MAX_CANDIDATOS]


def aplicar(
    escopo: str,
    sobras: Iterable[str],
    deputados: list[dict],
    ligados: dict[str, str],
    caminho: Path | None = None,
) -> list[str]:
    """Reaplica as decisões humanas: o que foi aceito entra em `ligados` (chave -> nome do
    deputado); o que foi recusado sai das sobras (não volta para a fila). Devolve as sobras
    ainda sem decisão. Decisão cujo deputado não está mais na lista é ignorada."""
    por_id = {_id(d): d["nome"] for d in deputados}
    aceitos, recusados = {}, set()
    for dec in decisoes(escopo, caminho):
        chave = comum.chave_nome(dec["nome_fonte"])
        if dec["decisao"] == "aceito" and dec["id_externo"] in por_id:
            aceitos[chave] = por_id[dec["id_externo"]]
        elif dec["decisao"] == "recusado":
            recusados.add(chave)
    restantes = []
    for chave in sobras:
        if chave in aceitos:
            ligados[chave] = aceitos[chave]
        elif chave not in recusados:
            restantes.append(chave)
    return restantes


def gravar_pendentes(
    escopo: str,
    sobras: Iterable[str],
    deputados: list[dict],
    totais: dict[str, tuple[int, Decimal]],
    destino: Path | None = None,
) -> list[dict]:
    """Escreve a fila do escopo (substitui a anterior). `totais`: chave -> (linhas, valor)."""
    fila = []
    for chave in sobras:
        linhas, valor = totais.get(chave, (0, Decimal(0)))
        fila.append(
            {
                "escopo": escopo,
                "nome_fonte": chave,
                "linhas": linhas,
                "valor": f"{valor:.2f}",
                "candidatos": json.dumps(sugerir(chave, deputados), ensure_ascii=False),
            }
        )
    destino = destino or pendentes_caminho(escopo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_PENDENTES)
        escritor.writeheader()
        escritor.writerows(fila)
    return fila


def pendentes(pasta: Path | None = None, caminho_decisoes: Path | None = None) -> list[dict]:
    """A fila de todos os escopos, sem o que já foi decidido; maior valor primeiro."""
    pasta = pasta or PENDENTES_DIR
    decididos = {
        (d["escopo"], comum.chave_nome(d["nome_fonte"])) for d in decisoes(None, caminho_decisoes)
    }
    fila = []
    for arquivo in sorted(pasta.glob("apelidos_pendentes_*.csv")):
        with arquivo.open(encoding="utf-8", newline="") as f:
            for lin in csv.DictReader(f):
                if (lin["escopo"], lin["nome_fonte"]) in decididos:
                    continue
                fila.append(
                    {
                        **lin,
                        "linhas": int(lin["linhas"]),
                        "valor": Decimal(lin["valor"]),
                        "candidatos": json.loads(lin["candidatos"]),
                    }
                )
    return sorted(fila, key=lambda x: -x["valor"])


def gravar_decisao(
    item: dict,
    decisao: str,
    revisor: str,
    id_externo: str = "",
    nome_deputado: str = "",
    observacao: str = "",
    caminho: Path | None = None,
) -> None:
    """`aceito` exige o deputado; `recusado` (nenhum candidato é a pessoa) vai sem deputado."""
    caminho = caminho or REVISADOS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(
            {
                "escopo": item["escopo"],
                "nome_fonte": item["nome_fonte"],
                "id_externo": id_externo,
                "nome_deputado": nome_deputado,
                "decisao": decisao,
                "revisado_por": revisor,
                "revisado_em": date.today().isoformat(),
                "observacao": observacao,
            }
        )
