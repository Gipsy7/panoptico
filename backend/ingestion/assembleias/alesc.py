"""Assembleia Legislativa de Santa Catarina (ALESC): deputados no cargo hoje e as
proposições de cada um, pelas páginas públicas da ALESC (não há API nem exportação).

- Deputados: a página oficial de deputados (www.alesc.sc.gov.br/deputados), com nome,
  partido e foto de cada um (40).
- Proposições: o e-Legis (portalelegis.alesc.sc.gov.br) lista as do "processo legislativo"
  (projetos, guardados com ementa) e as da "atividade parlamentar" (requerimentos,
  indicações, moções e pedidos de informação, só como contagem), 10 por página, filtradas
  por data de entrada. A autoria vem como "Deputado Altair Silva".

Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas, pela
gravação do conector SAPL. Votos, presença e gastos não estão nessas páginas.
"""

import argparse
import html
import re
import time
from datetime import UTC, date, datetime
from typing import Any

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "alesc"
DEPUTADOS = "https://www.alesc.sc.gov.br/deputados"
ELEGIS = "https://portalelegis.alesc.sc.gov.br"
LISTAS = ("processo-legislativo", "atividade-parlamentar")
PAUSA = 0.5
TIPOS = {
    "PL.": "Projeto de Lei",
    "PLC": "Projeto de Lei Complementar",
    "PEC": "Proposta de Emenda à Constituição",
    "PRS": "Projeto de Resolução",
    "PDL": "Projeto de Decreto Legislativo",
    "RQS": "Requerimento",
    "IND": "Indicação",
    "MOC": "Moção",
    "PIC": "Pedido de Informação",
    "OFL": "Ofício Legislativo",
    "RCC": "Requerimento de Comissões",
    "RQC": "Requerimento de Frente, Fórum, CPI ou Comissão Mista",
    "PSA": "Proposta de Sustação de Ato",
}
CARTAO = re.compile(
    r'<a href="/proposicoes/(?P<id>[A-Za-z0-9]+)">(?P<sigla>[^<]+)</a>\s*</h4>'
    r'(?P<corpo>.*?)(?=<div class="card card-alesc|<nav|$)',
    re.S,
)
CAMPO = r'fw-bold[^>]*>\s*{rotulo}\s*</div>\s*<div class="col-lg-10">(?P<valor>.*?)</div>'
TITULO = re.compile(r"^Deputad[oa]\s+", re.I)


def _limpo(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def deputados(pagina: str) -> list[dict[str, str]]:
    """Os cartões da página oficial: slug, nome, partido e foto."""
    vistos, resultado = set(), []
    for bloco in re.finditer(
        r'<a href="https://www\.alesc\.sc\.gov\.br/deputado/(?P<slug>[a-z0-9-]+)/">\s*'
        r'<div class="row align-items-center gx-3">(?P<corpo>.*?)</a>',
        pagina,
        re.S,
    ):
        slug, corpo = bloco.group("slug"), bloco.group("corpo")
        if slug in vistos:
            continue
        vistos.add(slug)
        nome = re.search(r'<h3 class="lab-title-news">(.*?)</h3>', corpo, re.S)
        partido = re.search(r'<span class="lab-button[^"]*"[^>]*>(.*?)</span>', corpo, re.S)
        foto = re.search(r'<img src="([^"]+)"', corpo)
        if nome:
            resultado.append({"slug": slug, "nome": _limpo(nome.group(1)),
                              "partido": _limpo(partido.group(1)) if partido else None,
                              "foto": foto.group(1) if foto else None})  # fmt: skip
    return resultado


def proposicoes(pagina: str) -> list[dict[str, Any]]:
    """Os cartões de uma página do e-Legis."""
    resultado = []
    for cartao in CARTAO.finditer(pagina):
        corpo = cartao.group("corpo")
        ementa = re.search(r'<p class="mb-1[^"]*"[^>]*>(.*?)</p>', corpo, re.S)
        entrada = re.search(CAMPO.format(rotulo="Entrada"), corpo, re.S)
        autoria = re.search(CAMPO.format(rotulo="Autoria"), corpo, re.S)
        itens = re.findall(r"<li>(.*?)</li>", autoria.group("valor"), re.S) if autoria else []
        autores = [_limpo(a) for a in itens]
        sigla = _limpo(cartao.group("sigla"))
        resultado.append(
            {
                "id": cartao.group("id"),
                "sigla": sigla,
                "ementa": _limpo(ementa.group(1)) if ementa else "",
                "entrada": _limpo(entrada.group("valor")) if entrada else "",
                "autores": [TITULO.sub("", a).strip() for a in autores],
            }
        )
    return resultado


def tipo_e_numero(sigla: str) -> tuple[str, int | None, int | None]:
    """'PL./0640/2026' -> ('Projeto de Lei', 640, 2026)."""
    achado = re.match(r"([A-Z]+\.?)\s*/?\s*(\d+)/(\d{4})", sigla.replace(" ", ""))
    if not achado:
        return sigla, None, None
    prefixo = achado.group(1)
    return TIPOS.get(prefixo, prefixo.rstrip(".")), int(achado.group(2)), int(achado.group(3))


def _data(valor: str) -> str | None:
    try:
        return datetime.strptime(valor.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def distribuir(props: list[dict], nomes: set[str]) -> dict[str, dict]:
    chave = {comum.chave_nome(n): n for n in nomes}
    por_deputado: dict[str, dict] = {n: {"contagem": {}, "projetos": []} for n in nomes}
    for p in props:
        tipo, numero, ano = tipo_e_numero(p["sigla"])
        for ordem, autor in enumerate(p["autores"]):
            nome = chave.get(comum.chave_nome(autor))
            if nome is None:
                continue
            dep = por_deputado[nome]
            dep["contagem"][tipo] = dep["contagem"].get(tipo, 0) + 1
            if p["lista"] == "processo-legislativo":
                dep["projetos"].append(
                    {
                        "id_externo": p["id"],
                        "tipo": tipo,
                        "numero": numero,
                        "ano": ano,
                        "ementa": p["ementa"],
                        "data_apresentacao": _data(p["entrada"]),
                        "em_tramitacao": None,
                        "primeiro_autor": ordem == 0,
                        "url": f"{ELEGIS}/proposicoes/{p['id']}",
                    }
                )
    return por_deputado


def baixar_lista(client: Any, lista: str, ano: int) -> list[dict]:
    """Todas as páginas de uma lista do e-Legis num ano, uma requisição por vez."""
    params = {"inicio": f"{ano}-01-01", "fim": f"{ano}-12-31"}
    resultado, pagina = [], 1
    while True:
        time.sleep(PAUSA)
        resposta = comum._get(
            client, f"{ELEGIS}/proposicoes/{lista}", {**params, "page": pagina}, 4
        )
        itens = proposicoes(resposta.text)
        for item in itens:
            item["lista"] = lista
        resultado += itens
        total = re.search(r"Exibindo [\d.]+ - ([\d.]+) de ([\d.]+)", resposta.text)
        if not itens or not total or total.group(1) == total.group(2):
            return resultado
        pagina += 1


def coletar(hoje: date) -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, DEPUTADOS, None, 4).text)
        props = []
        for ano in (hoje.year - 1, hoje.year):
            for nome_lista in LISTAS:
                props += baixar_lista(client, nome_lista, ano)
    autoria = distribuir(props, {d["nome"] for d in lista})
    vereadores = [
        {
            "id_externo": d["slug"][:20],
            "nome": d["nome"],
            "nome_completo": None,
            "partido": d["partido"],
            "foto_url": d["foto"],
            "email": None,
            "telefone": None,
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": autoria[d["nome"]]["contagem"],
            "projetos": autoria[d["nome"]]["projetos"],
            "sessoes": None,
            "presencas": None,
        }
        for d in lista
    ]
    return {
        "base": ELEGIS,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar(date.today())
    if len(casa["vereadores"]) < 30:  # a ALESC tem 40 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALESC; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="SC")
        session.add(
            FonteIngestao(fonte=FONTE, url=ELEGIS, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALESC: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
