"""Assembleia Legislativa do Amapá (ALAP): deputados em exercício e projetos de autoria, pelo
site da Casa e pelo portal do eLegis.

- Deputados: `al.ap.leg.br/pagina.php?pg=exibir_legislatura` (a legislatura atual, 24 deputados;
  nome parlamentar, nome completo e partido vêm na dica de cada foto; a foto, no cartão).
- Projetos: `elegis.al.ap.leg.br/portal/proposicoes?tipo_proposicao=T&ano=AAAA&page=N`, a
  pesquisa pública do portal (GET, sem login): data, "Projeto de Lei Ordinária nº 0102/26-AL",
  autor ("Deputado Fulano ou Poder Executivo") e ementa. Entram projetos de lei, de lei
  complementar, PEC, decretos legislativos e resoluções do ano atual e do anterior, de autoria
  de deputado (nome exato); indicações e requerimentos não entram. O portal avisa que o
  Processo Legislativo está em migração para o eLegis e pode estar defasado.

Sem votos, presença nem gastos nos dados públicos. O `robots.txt` do eLegis libera tudo; o de
`al.ap.leg.br` responde 403 (para qualquer cliente) e as páginas públicas respondem normalmente.
Uma requisição por vez, com pausa. Ver docs/DECISOES.md.
"""

import argparse
import html
import re
import time
from datetime import date

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alap"
SITE = "https://al.ap.leg.br/"
LISTA = SITE + "pagina.php?pg=exibir_legislatura"
ELEGIS = "https://elegis.al.ap.leg.br/portal/proposicoes"
PAUSA = 1.0
MAX_PAGINAS = 80
TIPOS = {  # código do filtro do portal -> (sigla, tipo)
    "1": ("PL", "Projeto de Lei"),
    "2": ("PLC", "Projeto de Lei Complementar"),
    "4": ("PEC", "Proposta de Emenda à Constituição"),
    "10": ("PDL", "Projeto de Decreto Legislativo"),
    "9": ("PR", "Projeto de Resolução"),
}
CARTAO = re.compile(
    r"iddeputado=(?P<id>\d+)\"[^>]*Tip\('<b>Dep\.</b> (?P<nome>[^<]*)<br>"
    r"<b>Nome Completo:</b> (?P<civil>[^<]*)<br><b>Partido:</b> (?P<partido>[^<]*)<br>"
    r".*?<img class=\"foto-deputado\" src=\"(?P<foto>[^\"]*)\"",
    re.S,
)
LINHA = re.compile(
    r"<tr>\s*<td>(?P<data>\d\d/\d\d/\d{4})</td>\s*<td>\s*(?P<titulo>[^<]*?)\s*</td>\s*"
    r"<td>(?P<autor>[^<]*)</td>\s*<td>(?P<ementa>[^<]*)</td>.*?/portal/proposicao/(?P<id>\d+)",
    re.S,
)
NUMERO = re.compile(r"n[º°o]?\s*(\d+)/(\d{2})", re.I)


def deputados(pagina: str) -> list[dict]:
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c["id"] in vistos:
            continue
        vistos.add(c["id"])
        partido = html.unescape(c["partido"]).strip()
        sigla = re.search(r"\(([^)]+)\)\s*$", partido)
        resultado.append(
            {
                "id": c["id"],
                "nome": html.unescape(c["nome"]).strip(),
                "civil": html.unescape(c["civil"]).strip(),
                "partido": sigla.group(1) if sigla else partido,
                "foto": SITE + html.unescape(c["foto"]).strip().replace(" ", "%20"),
            }
        )
    return resultado


def proposicoes(pagina: str, sigla: str, tipo: str) -> list[dict]:
    """Linhas da tabela do portal: autor limpo do tratamento e número/ano do título."""
    resultado = []
    for m in LINHA.finditer(pagina):
        numero = NUMERO.search(html.unescape(m["titulo"]))
        if numero is None:
            continue
        resultado.append(
            {
                "id": m["id"],
                "autor": re.sub(r"^Deputad[oa]\s+", "", html.unescape(m["autor"]).strip()),
                "projeto": base.projeto(
                    sigla,
                    tipo,
                    int(numero[1]),
                    2000 + int(numero[2]),
                    html.unescape(m["ementa"]),
                    "-".join(reversed(m["data"].split("/"))),
                    f"https://elegis.al.ap.leg.br/portal/proposicao/{m['id']}",
                ),
            }
        )
    return resultado


def baixar(client, codigo: str, ano: int) -> list[dict]:
    sigla, tipo = TIPOS[codigo]
    resultado, vistos = [], set()
    for pagina in range(1, MAX_PAGINAS + 1):
        time.sleep(PAUSA)
        texto = comum._get(
            client, ELEGIS, {"tipo_proposicao": codigo, "ano": ano, "page": pagina}, 4
        ).content.decode("utf-8", "replace")
        novas = [p for p in proposicoes(texto, sigla, tipo) if p["id"] not in vistos]
        if not novas:
            return resultado
        vistos |= {p["id"] for p in novas}
        resultado += novas


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        por_nome = {comum.chave_nome(d["nome"]): d["id"] for d in lista}
        autoria: dict[str, list[dict]] = {d["id"]: [] for d in lista}
        for ano in (hoje.year - 1, hoje.year):
            for codigo in TIPOS:
                for p in baixar(client, codigo, ano):
                    dono = por_nome.get(comum.chave_nome(p["autor"]))
                    if dono:
                        autoria[dono].append(p["projeto"])
    registros = []
    for d in lista:
        projetos = autoria[d["id"]]
        tipos: dict[str, int] = {}
        for p in projetos:
            tipos[p["tipo"]] = tipos.get(p["tipo"], 0) + 1
        registros.append(base.registro(d, projetos=projetos, por_tipo=tipos))
    return base.casa(LISTA, registros)


def executar() -> int:
    # A ALAP tem 24 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="AP", sigla="ALAP", url=LISTA, minimo=20
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
