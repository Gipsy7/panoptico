"""Assembleia Legislativa de Goiás (ALEGO): deputados em exercício, verba indenizatória, projetos
de autoria e presença em plenário, pelo portal, pela API do portal da transparência e pela API
de dados abertos do processo legislativo (a do PLE, igual à da ALBA, da ALES e da ALESE).

- Deputados: `portal.al.go.leg.br/deputados/em-exercicio`, tabela renderizada no servidor com
  nome, partido, telefones, e-mail do gabinete e o código do perfil.
- Verba indenizatória: a página de dados abertos (`transparencia.al.go.leg.br/dados-abertos`) é
  montada no navegador (AngularJS) e lista as rotas JSON no próprio script da página;
  `api/transparencia/verbas_indenizatorias.json?ano=&mes=&todos=true` devolve, por deputado e mês,
  o valor apresentado e o indenizado (usamos o indenizado), e `verbas_indenizatorias/periodos`
  diz quais meses existem. O código do deputado é o mesmo do portal.

- Projetos e presença: `alegodigital.al.go.leg.br/api/publico/` (documentada na página
  `dados-abertos.aspx` do sistema; ver `ple.py`): `parlamentar/` traz os deputados com a
  frequência em plenário por ano (presente, falta justificada, falta não justificada, licença) e
  `proposicao/?ano=&sigla=` as proposições. O código do deputado ali não é o do portal: ligamos
  pelo nome parlamentar ou civil, só por igualdade exata (com a ajuda do nome de urna e civil do
  TSE). A API traz o CPF do autor; não o guardamos. O `robots.txt` desse sistema responde 406
  (página de erro, sem regra); a API é publicada como dados abertos para uso por programa.

Votos nominais não têm rota pública. O `robots.txt` do portal da transparência só veda o quadro
de remuneração. Uma requisição por vez, com pausa. Ver docs/DECISOES.md.
"""

import argparse
import html
import re
import time
from datetime import date
from decimal import Decimal

from app.db import SessionLocal
from ingestion import comum
from ingestion.assembleias import base, ple

FONTE = "alego"
PORTAL = "https://portal.al.go.leg.br"
LISTA = PORTAL + "/deputados/em-exercicio"
API = "https://transparencia.al.go.leg.br/api/transparencia/"
PAUSA = 1.0
CATEGORIA = "Verba indenizatória"
PLE = "https://alegodigital.al.go.leg.br/api/publico/"
PROJETOS = {
    "PLO": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PDL": "Projeto de Decreto Legislativo",
    "RES": "Projeto de Resolução",
}
CONTAGEM = {"REQ": "Requerimento", "PLTC": "Projeto de Lei de Título de Cidadão"}
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


def coletar(hoje: date, tse: list[tuple[str, str]] | None = None) -> dict:
    """`tse`: (nome de urna, nome civil) das candidaturas da UF, para ligar a API ao portal."""
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
        client.headers["Accept"] = "application/json"
        parlamentares, autoria = ple.deputados_e_autoria(
            client, PLE, set(anos), pausa=PAUSA, projetos=PROJETOS, contagem=CONTAGEM,
            por_sigla=True, so_ativos=False,
        )  # fmt: skip
        # A situação na API às vezes não é a do portal (Amilton Filho, "fora de exercício" na
        # API e em exercício no portal, 29/10/2026): quem diz quem está no cargo é o portal.
    da_api = ligar_api(parlamentares, lista, tse or [])
    registros = []
    for d in lista:
        p = da_api.get(d["id"])
        sessoes, presencas = ple.frequencia(p, set(anos)) if p else (None, None)
        dep = autoria.get(str(p["parlamentarID"])) if p else None
        registros.append(
            base.registro(
                d,
                gastos=todos.get(d["id"]),
                projetos=dep["projetos"] if dep else None,
                por_tipo=dep["contagem"] if dep else None,
                sessoes=sessoes,
                presencas=presencas,
            )
        )
    sem = [d["nome"] for d in lista if d["id"] not in da_api]
    if sem:
        print(f"  sem par na API do processo legislativo: {', '.join(sem)}", flush=True)
    return base.casa(LISTA, registros)


def ligar_api(
    parlamentares: list[dict], lista: list[dict], tse: list[tuple[str, str]]
) -> dict[str, dict]:
    """Código do deputado no portal -> registro dele na API do processo legislativo, pelo nome
    parlamentar ou civil da API igual ao nome do portal (direto ou via TSE). Só par único."""
    chaves: dict[str, set[int]] = {}
    for i, p in enumerate(parlamentares):
        for nome in (p.get("parlamentarNome"), p.get("parlamentarRazaoSocial")):
            if nome:
                chaves.setdefault(comum.chave_nome(nome), set()).add(i)
    ligados, _ = base.ligar_nomes_exatos(set(chaves), lista, tse)
    por_nome = {d["nome"]: d["id"] for d in lista}
    candidatos: dict[str, set[int]] = {}
    for chave, nome in ligados.items():
        candidatos.setdefault(por_nome[nome], set()).update(chaves[chave])
    usados = [i for c in candidatos.values() for i in c]
    return {
        id_: parlamentares[next(iter(c))]
        for id_, c in candidatos.items()
        if len(c) == 1 and usados.count(next(iter(c))) == 1
    }


def executar() -> int:
    # A ALEGO tem 41 cadeiras: lista curta é falha da fonte.
    with SessionLocal() as session:
        tse = base.nomes_do_tse(session, "GO")
    return base.gravar(
        coletar(date.today(), tse), fonte=FONTE, uf="GO", sigla="ALEGO", url=LISTA, minimo=35
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
