"""Assembleia Legislativa do Maranhão (ALEMA): deputados em exercício pelo site oficial e as
proposições de autoria pela API do ALEMALEGIS, o sistema legislativo da Casa.

- Deputados: `www.al.ma.leg.br/sitealema/deputados/` (cartões com nome, partido e foto; os
  "Deputados licenciados", listados abaixo, ficam de fora). A
  lista da API (`parliamentary`) traz as quatro legislaturas e um `ACTIVE` que não diz quem
  está no cargo; por isso a lista do site é a de quem está em exercício.
- Proposições: `alemalegis.al.ma.leg.br/api/v1/public/legislative-matter/filter/access?year=`,
  a mesma rota pública que o portal Angular chama (sem login), 100 por página. Cada matéria traz
  o tipo, a ementa, a data e o autor por nome. Projetos (lei, lei complementar, PEC, decreto
  legislativo e resolução) entram com a ementa; indicações, requerimentos e moções, só como
  contagem. O autor é ligado ao deputado só por nome exato (do site ou do cadastro da API).

Há rotas de votos e de presença na API, mas fora desta coleta mínima. O servidor não publica
`robots.txt` (a rota cai na página do aplicativo). Uma requisição por vez, com pausa.
"""

import argparse
import html
import re
import time
from datetime import date

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alema"
SITE = "https://www.al.ma.leg.br/sitealema/deputados/"
API = "https://alemalegis.al.ma.leg.br/api/v1/public/"
PAUSA = 1.0
PROJETOS = {
    "PLO": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PRE": "Projeto de Resolução",
}
CONTAGEM = {"IND": "Indicação", "REQ": "Requerimento", "MOC": "Moção"}
CARTAO = re.compile(
    r'<div class="news-card-image">\s*<img src="(?P<foto>[^"]+)" alt="[^"]*">\s*</div>\s*'
    r'<div class="news-card-content">\s*'
    r'<h3 class="news-card-title"><a href="[^"]*/deputado/(?P<id>[^/"]+)/">'
    r"(?P<nome>[^<]*)</a></h3>\s*"
    r'<p class="news-card-chapeu">(?P<partido>[^<]*)</p>'
)


def deputados(pagina: str) -> list[dict]:
    """Os cartões acima do título "Deputados licenciados" (quem está no cargo)."""
    pagina = pagina.split("Deputados licenciados")[0]
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c["id"] in vistos:
            continue
        vistos.add(c["id"])
        resultado.append(
            {
                "id": c["id"],
                "nome": html.unescape(c["nome"]).strip(),
                "partido": html.unescape(c["partido"]).strip() or None,
                "foto": html.unescape(c["foto"]),
            }
        )
    return resultado


# Autor que a API escreve diferente do site e do cadastro (conferido contra a lista do site).
APELIDOS = {"JANAINA LIMA": "janaina"}


def apelidos(cadastro: list[dict], lista: list[dict]) -> dict[str, str]:
    """Nome (chave) -> id do deputado, com o nome parlamentar e o civil do cadastro da API
    quando um deles coincide exatamente com o nome do site."""
    por_nome = {comum.chave_nome(d["nome"]): d["id"] for d in lista}
    ids = {d["id"] for d in lista}
    for d in lista:  # o endereço do cartão ("andreia-rezende") é o nome parlamentar da API
        por_nome.setdefault(comum.chave_nome(d["id"].replace("-", " ")), d["id"])
    por_nome.update({k: v for k, v in APELIDOS.items() if v in ids})
    for c in cadastro:
        chaves = [comum.chave_nome(c.get("parliamentaryName")), comum.chave_nome(c.get("fullName"))]
        dono = next((por_nome[k] for k in chaves if k in por_nome), None)
        if dono:
            for k in chaves:
                por_nome.setdefault(k, dono)
    return por_nome


def distribuir(materias: list[dict], por_nome: dict[str, str]) -> dict[str, dict]:
    resultado: dict[str, dict] = {i: {"tipos": {}, "projetos": []} for i in set(por_nome.values())}
    for m in materias:
        dono = por_nome.get(comum.chave_nome(m.get("authorNames")))
        sigla = (m.get("matterTypeSigla") or "").strip()
        if dono is None or (sigla not in PROJETOS and sigla not in CONTAGEM):
            continue
        tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        dep = resultado[dono]
        dep["tipos"][tipo] = dep["tipos"].get(tipo, 0) + 1
        if sigla in PROJETOS:
            dep["projetos"].append(
                base.projeto(
                    sigla,
                    tipo,
                    m["number"],
                    int(m["year"]),
                    m.get("ement") or "",
                    (m.get("presentationDate") or "")[:10] or None,
                    f"{API}legislative-matter/{m['id']}",
                )
            )
    return resultado


def baixar_materias(client, ano: int) -> list[dict]:
    resultado, pagina = [], 0
    while True:
        time.sleep(PAUSA)
        d = comum.get_json(
            client,
            API + "legislative-matter/filter/access",
            {"page": pagina, "size": 100, "year": ano},
            4,
        )
        resultado += d.get("content") or []
        pagina += 1
        if pagina >= int(d.get("totalPages") or 0):
            return resultado


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        client.headers["Accept"] = "application/json, text/html"
        lista = deputados(comum._get(client, SITE, None, 4).content.decode("utf-8", "replace"))
        cadastro = comum.get_json(client, API + "parliamentary/find-all-partial")
        materias = []
        for ano in (hoje.year - 1, hoje.year):
            materias += baixar_materias(client, ano)
    autoria = distribuir(materias, apelidos(cadastro, lista))
    return base.casa(
        SITE,
        [
            base.registro(
                d, projetos=autoria[d["id"]]["projetos"], por_tipo=autoria[d["id"]]["tipos"]
            )
            for d in lista
        ],
    )


def executar() -> int:
    # A ALEMA tem 42 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="MA", sigla="ALEMA", url=API, minimo=35
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
