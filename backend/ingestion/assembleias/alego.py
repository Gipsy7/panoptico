"""Assembleia Legislativa de Goiás (ALEGO): deputados em exercício e verba indenizatória, pelo
portal e pela API do portal da transparência da Casa.

- Deputados: `portal.al.go.leg.br/deputados/em-exercicio`, tabela renderizada no servidor com
  nome, partido, telefones, e-mail do gabinete e o código do perfil.
- Verba indenizatória: a página de dados abertos (`transparencia.al.go.leg.br/dados-abertos`) é
  montada no navegador (AngularJS) e lista as rotas JSON no próprio script da página;
  `api/transparencia/verbas_indenizatorias.json?ano=&mes=&todos=true` devolve, por deputado e mês,
  o valor apresentado e o indenizado (usamos o indenizado), e `verbas_indenizatorias/periodos`
  diz quais meses existem. O código do deputado é o mesmo do portal.

Projetos, votos e presença não têm rota JSON pública (o item "Requerimentos" dos dados abertos só
aponta para a página inicial). O `robots.txt` do portal da transparência só veda o quadro de
remuneração. Uma requisição por vez, com pausa. Ver docs/DECISOES.md.
"""

import argparse
import html
import re
import time
from datetime import date
from decimal import Decimal

from ingestion import comum
from ingestion.assembleias import base

FONTE = "alego"
PORTAL = "https://portal.al.go.leg.br"
LISTA = PORTAL + "/deputados/em-exercicio"
API = "https://transparencia.al.go.leg.br/api/transparencia/"
PAUSA = 1.0
CATEGORIA = "Verba indenizatória"
LINHA = re.compile(
    r"<tr[^>]*data-filter-key[^>]*>(?P<corpo>.*?)</tr>",
    re.S,
)
NOME = re.compile(r"href=/?deputados/perfil/(?P<id>\d+)>(?P<nome>[^<]*)</a>")
PARTIDO = re.compile(r'data-title="Partido">(?P<partido>[^<]*)</td>')
EMAIL = re.compile(r"mailto:([^\"'> ]+)")


def deputados(pagina: str) -> list[dict]:
    resultado, vistos = [], set()
    for linha in LINHA.finditer(pagina):
        corpo = linha["corpo"]
        nome = NOME.search(corpo)
        if nome is None or nome["id"] in vistos:
            continue
        vistos.add(nome["id"])
        partido = (
            html.unescape(PARTIDO.search(corpo)["partido"]).strip() if PARTIDO.search(corpo) else ""
        )
        sigla = re.search(r"\(([^)]+)\)\s*$", partido)
        email = EMAIL.search(corpo)
        resultado.append(
            {
                "id": nome["id"],
                "nome": html.unescape(nome["nome"]).strip(),
                "partido": sigla.group(1) if sigla else partido or None,
                "email": email.group(1) if email else None,
                "foto": None,
            }
        )
    return resultado


def verbas(registros: list[dict]) -> dict[str, list[dict]]:
    """Código do deputado -> uma linha por mês com o valor indenizado."""
    resultado: dict[str, list[dict]] = {}
    for r in registros:
        valor = Decimal(str(r.get("valor_indenizado") or 0))
        resultado.setdefault(str(r["deputado"]["id"]), []).append(
            {"ano": int(r["ano"]), "mes": int(r["mes"]), "categoria": CATEGORIA, "valor": valor}
        )
    return resultado


def coletar(hoje: date) -> dict:
    anos = (hoje.year - 1, hoje.year)
    with comum.criar_cliente() as client:
        client.headers["Accept"] = (
            "text/html,application/json;q=0.9,*/*;q=0.8"  # o portal dá 500 a "só JSON"
        )
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        periodos = comum.get_json(client, API + "verbas_indenizatorias/periodos")
        meses = [(p["ano"], m) for p in periodos if p["ano"] in anos for m in sorted(p["meses"])]
        todos: dict[str, list[dict]] = {}
        for ano, mes in sorted(meses):
            time.sleep(PAUSA)
            dados = comum.get_json(
                client,
                API + "verbas_indenizatorias.json",
                {"ano": ano, "mes": mes, "todos": "true"},
                4,
            )
            for k, v in verbas(dados).items():
                todos.setdefault(k, []).extend(v)
    return base.casa(LISTA, [base.registro(d, gastos=todos.get(d["id"])) for d in lista])


def executar() -> int:
    # A ALEGO tem 41 cadeiras: lista curta é falha da fonte.
    return base.gravar(
        coletar(date.today()), fonte=FONTE, uf="GO", sigla="ALEGO", url=LISTA, minimo=35
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
