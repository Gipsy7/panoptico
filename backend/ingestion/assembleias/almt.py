"""Assembleia Legislativa de Mato Grosso (ALMT): deputados no cargo hoje, pelas páginas
públicas do site (www.al.mt.gov.br/parlamento/deputados e a ficha de cada um).

- Lista: 24 cartões com nome, partido, foto e o código do perfil.
- Ficha: `/parlamento/deputados/{id}/perfil` dá o nome civil.

Não entra mais nada:
- a API da ALMT (api.al.mt.gov.br, com `ssl/parlamentar`, `ssl/proposicao`, votações...) exige
  OAuth 2.0 e é, nas palavras da própria página, para fornecedores da instituição. Sem
  credencial pública, não usamos;
- o `robots.txt` do site proíbe `/proposicao?` (a pesquisa e a paginação de proposições),
  `/parlamento/ordem-do-dia?`, `/parlamento/documentos/parlamentares?` e
  `/transparencia/pesquisa/`. Respeitamos.
Uma requisição por vez, com pausa. Ver docs/DECISOES.md.
"""

import argparse
import html
import re
import time
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "almt"
SITE = "https://www.al.mt.gov.br"
LISTA = SITE + "/parlamento/deputados"
PAUSA = 0.5
CARTAO = re.compile(
    r'<a href="/parlamento/deputados/(?P<id>\d+)/perfil">\s*'
    r'<img[^>]*src="(?P<foto>[^"]*)"[^>]*>\s*</a>\s*'
    r'<div class="card-body">\s*<span class="badge[^"]*">\s*(?P<partido>.*?)\s*</span>\s*'
    r'<h6 class="card-title[^"]*">(?P<nome>.*?)</h6>',
    re.S,
)


def _limpo(trecho: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def deputados(pagina: str) -> list[dict[str, str | None]]:
    vistos, resultado = set(), []
    for c in CARTAO.finditer(pagina):
        if c.group("id") in vistos:
            continue
        vistos.add(c.group("id"))
        resultado.append(
            {
                "id": c.group("id"),
                "nome": comum.nome_proprio(_limpo(c.group("nome"))),
                "partido": _limpo(c.group("partido")) or None,
                "foto": html.unescape(c.group("foto")) or None,
            }
        )
    return resultado


def nome_civil(pagina: str) -> str | None:
    m = re.search(r"Nome civil:\s*(?:</?[^>]+>\s*)*([^<]+)", pagina)
    return comum.nome_proprio(_limpo(m.group(1))) if m else None


def coletar() -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(comum._get(client, LISTA, None, 4).content.decode("utf-8", "replace"))
        for d in lista:
            time.sleep(PAUSA)
            try:
                pagina = comum._get(client, f"{LISTA}/{d['id']}/perfil", None, 3)
                d["civil"] = nome_civil(pagina.content.decode("utf-8", "replace"))
            except Exception as erro:  # uma ficha fora do ar não derruba a lista
                print(f"  ficha {d['id']}: {erro.__class__.__name__}", flush=True)
    vereadores = [
        {
            "id_externo": d["id"],
            "nome": d["nome"],
            "nome_completo": d.get("civil"),
            "partido": d["partido"],
            "foto_url": d["foto"],
            "email": None,
            "telefone": None,
            "titular": True,
            "em_exercicio": True,
            "inicio": None,
            "fim": None,
            "proposicoes_por_tipo": {},
            "projetos": [],
            "sessoes": None,
            "presencas": None,
        }
        for d in lista
    ]
    return {
        "base": LISTA,
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar()
    if len(casa["vereadores"]) < 20:  # a ALMT tem 24 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALMT; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="MT")
        session.add(
            FonteIngestao(fonte=FONTE, url=LISTA, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALMT: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
