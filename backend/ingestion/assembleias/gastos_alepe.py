"""Assembleia Legislativa de Pernambuco (ALEPE): verba indenizatória dos deputados, pelas rotas
JSON que o próprio portal da transparência (`transparencia.alepe.pe.gov.br/financas`, página
montada no navegador) chama, sem login, em `alepe.pe.gov.br/servicos/transparencia/`:

- `dep/deputados.php?leg=-16`: os deputados (id, nome, partido) que o portal oferece;
- `adm/verbaindenizatoria-dep-meses.php?dep=ID&ano=AAAA`: os meses com prestação de contas;
- `adm/verbaindenizatoria.php?dep=ID&ano=AAAA&mes=M`: os documentos do mês, com o total;
- `adm/verbaindenizatorianotas.php?docid=N`: as notas do documento (rubrica, data, valor; o
  fornecedor não é guardado);
- `adm/verbaindenizatoria-rubricas.php?ano=AAAA`: o nome de cada rubrica.

Somamos por deputado, mês e rubrica, no ano anterior e no atual, e conferimos a soma das
notas de cada documento com o total que o próprio documento traz. Valores com vírgula
decimal ("13816,6"). O `robots.txt` do portal libera tudo. Uma requisição por vez, com pausa.
"""

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from ingestion import comum
from ingestion.assembleias import gastos

FONTE = "alepe_gastos"
URL = "https://transparencia.alepe.pe.gov.br/financas"
API = "https://www.alepe.pe.gov.br/servicos/transparencia/"
PAUSA = 0.3
TENTATIVAS_NOTAS = 4


def _json(client: httpx.Client, caminho: str, params: dict) -> tuple[bytes, object]:
    gastos.pausar(PAUSA)
    conteudo = comum._get(client, API + caminho, params, 4).content
    return conteudo, json.loads(conteudo.decode("utf-8-sig") or "[]")


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    hoje = hoje or date.today()
    arquivos: gastos.Arquivos = {}
    bruto, deputados = _json(client, "dep/deputados.php", {"leg": -16})
    arquivos["deputados.json"] = bruto
    for ano in (hoje.year - 1, hoje.year):
        arquivos[f"rubricas_{ano}.json"] = _json(
            client, "adm/verbaindenizatoria-rubricas.php", {"ano": ano}
        )[0]
        for dep in deputados:  # type: ignore[union-attr]
            _, meses = _json(
                client, "adm/verbaindenizatoria-dep-meses.php", {"dep": dep["id"], "ano": ano}
            )
            for m in meses:  # type: ignore[union-attr]
                bruto, docs = _json(
                    client,
                    "adm/verbaindenizatoria.php",
                    {"dep": dep["id"], "ano": ano, "mes": m["mes"]},
                )
                arquivos[f"docs_{dep['id']}_{ano}_{int(m['mes']):02d}.json"] = bruto
                for doc in docs:  # type: ignore[union-attr]
                    arquivos[f"notas_{doc['docid']}.json"] = notas_do_documento(client, doc)
    return arquivos


def notas_do_documento(client: httpx.Client, doc: dict) -> bytes:
    """As notas de um documento. A rota às vezes devolve lista vazia para documento com total
    (visto em 124 de ~900 em 29/10/2026; na repetição vêm as notas): tenta de novo, com pausa
    maior. Se continuar vazia, a conferência com o total em `ler` aborta a carga."""
    bruto = b"[]"
    for tentativa in range(TENTATIVAS_NOTAS):
        if tentativa:
            gastos.pausar(PAUSA * 10 * tentativa)
        bruto, notas = _json(client, "adm/verbaindenizatorianotas.php", {"docid": doc["docid"]})
        if notas or not (gastos.valor_br(doc.get("total")) or 0):
            break
    return bruto


def _carregar(conteudo: bytes) -> list:
    return json.loads(conteudo.decode("utf-8-sig") or "[]")


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    """Uma linha por nota, com o nome do deputado e a rubrica. Aborta se a soma das notas de
    um documento não bater com o total do documento (número que não bate é bug)."""
    nomes = {str(d["id"]): d["nome"].strip() for d in _carregar(arquivos["deputados.json"])}
    rubricas: dict[tuple[int, int], str] = {}
    for nome, conteudo in arquivos.items():
        if nome.startswith("rubricas_"):
            ano = int(nome[9:13])
            for r in _carregar(conteudo):
                rubricas[(ano, int(r["numero_categoria"]))] = " ".join(
                    r["nome_categoria"].split()
                ).capitalize()
    resultado = []
    for nome in sorted(arquivos):
        if not nome.startswith("docs_"):
            continue
        _, dep, ano, mes = nome.removesuffix(".json").split("_")
        for doc in _carregar(arquivos[nome]):
            notas = _carregar(arquivos.get(f"notas_{doc['docid']}.json", b"[]"))
            soma = Decimal(0)
            for n in notas:
                valor = gastos.valor_br(n["valor"]) or Decimal(0)
                soma += valor
                resultado.append(
                    {
                        "nome": nomes.get(dep, dep),
                        "ano": int(ano),
                        "mes": int(mes),
                        "categoria": rubricas.get(
                            (int(ano), int(n["rubrica"])), f"Rubrica {n['rubrica']}"
                        ),
                        "valor": valor,
                    }
                )
            total = gastos.valor_br(doc.get("total")) or Decimal(0)
            if soma != total:
                raise ValueError(
                    f"ALEPE: documento {doc['docid']} soma {soma} nas notas e {total} no total."
                )
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="PE", sigla="ALEPE", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/alepe_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
