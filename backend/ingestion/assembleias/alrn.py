"""Assembleia Legislativa do Rio Grande do Norte (ALRN): deputados em exercício e proposições de
autoria, pelo site e pela API do portal de Transparência Legislativa.

- Deputados: `al.rn.leg.br/deputados` (24 cartões com nome, partido e foto, e o código do
  perfil) e `api-transparencialegislativa.al.rn.leg.br/elegis-api-transp-legislativa/parlamentar/`,
  a API que o portal de transparência legislativa chama (sem login), que traz os 24 em exercício
  com o código da iniciativa de cada um. A API devolve também o CPF; não o guardamos.
- Proposições: `processo?iniciativa=ID&pagina=N&tamanhoPagina=100`, da mais nova para a mais
  antiga; paramos ao passar do ano anterior. Projetos (lei, lei complementar, emenda à
  Constituição, decreto legislativo e resolução) entram com a ementa; requerimentos, pedidos de
  informação e moções, só como contagem.

Sem votos nominais por deputado nem verba de gabinete nesta coleta (a rota `ultimas-votacoes`
traz só o resultado). O `robots.txt` do site libera tudo. Uma requisição por vez, com pausa.
"""

import argparse
import html
import re
import time
from datetime import date

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alrn"
SITE = "https://al.rn.leg.br/"
LISTA = SITE + "deputados"
API = "https://api-transparencialegislativa.al.rn.leg.br/elegis-api-transp-legislativa/"
PAUSA = 1.0
PROJETOS = {
    "PL": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "PR": "Projeto de Resolução",
}
CONTAGEM = {"REQ": "Requerimento", "REQINFOR": "Pedido de Informação", "MOC": "Moção"}
CARTAO = re.compile(
    r'deputado/(?P<id>\d+)/[a-z0-9-]+"[^>]*>.*?url\(\'(?P<foto>[^\']*)\'\).*?'
    r'name-deputies">(?P<nome>[^<]*)</strong>\s*<p class="party-deputies">(?P<partido>[^<]*)</p>',
    re.S,
)


def deputados(pagina: str) -> list[dict]:
    resultado, vistos = [], set()
    for c in CARTAO.finditer(pagina):
        if c["id"] in vistos:
            continue
        vistos.add(c["id"])
        sigla = re.search(r"\(([^)]+)\)\s*$", html.unescape(c["partido"]))
        resultado.append(
            {
                "id": c["id"],
                "nome": html.unescape(c["nome"]).strip(),
                "partido": sigla.group(1) if sigla else None,
                "foto": c["foto"],
            }
        )
    return resultado


def iniciativas(cadastro: list[dict]) -> dict[str, int]:
    """Chave do nome parlamentar ('DEPUTADO FULANO' sem o tratamento) -> id da iniciativa."""
    resultado = {}
    for p in cadastro:
        ativa = [i["id"] for i in p.get("iniciativas", []) if i["tipo"] == "PARLAMENTAR"]
        nome = re.sub(r"^DEPUTAD[OA]\s+", "", p["nomeParlamentar"].strip())
        if ativa:
            resultado[comum.chave_nome(nome)] = ativa[-1]
    return resultado


def classificar(processos: list[dict]) -> tuple[dict[str, int], list[dict]]:
    tipos: dict[str, int] = {}
    projetos = []
    for p in processos:
        prop = p.get("propositura") or {}
        sigla = ((prop.get("tipo") or {}).get("sigla") or "").strip()
        if sigla not in PROJETOS and sigla not in CONTAGEM:
            continue
        tipo = PROJETOS.get(sigla) or CONTAGEM[sigla]
        tipos[tipo] = tipos.get(tipo, 0) + 1
        if sigla in PROJETOS:
            projetos.append(
                base.projeto(
                    sigla,
                    tipo,
                    prop["numero"],
                    int(prop["ano"]),
                    p.get("ementa") or "",
                    (p.get("dataEntrada") or "")[:10] or None,
                    f"{API}processo/{p['id']}",
                )
            )
    return tipos, projetos


def baixar_processos(client, iniciativa: int, desde: int) -> list[dict]:
    resultado, pagina = [], 0
    while True:
        time.sleep(PAUSA)
        d = comum.get_json(
            client,
            API + "processo",
            {"pagina": pagina, "tamanhoPagina": 100, "iniciativa": iniciativa},
            4,
        )
        lote = d.get("dados") or []
        resultado += [p for p in lote if int(p["ano"]) >= desde]
        pagina += 1
        if not lote or int(lote[-1]["ano"]) < desde or len(resultado) >= int(d.get("total") or 0):
            return resultado


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        ids = iniciativas(comum.get_json(client, API + "parlamentar/").get("dados", []))
        registros = []
        for d in lista:
            iniciativa = ids.get(comum.chave_nome(d["nome"]))
            if iniciativa is None:
                print(f"  {d['nome']}: sem iniciativa na API; entra sem proposições", flush=True)
                registros.append(base.registro(d))
                continue
            tipos, projetos = classificar(baixar_processos(client, iniciativa, hoje.year - 1))
            registros.append(base.registro(d, projetos=projetos, por_tipo=tipos))
    return base.casa(LISTA, registros)


def executar() -> int:
    # A ALRN tem 24 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="RN", sigla="ALRN", url=API, minimo=20
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
