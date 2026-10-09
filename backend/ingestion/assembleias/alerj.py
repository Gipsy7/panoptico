"""Assembleia Legislativa do Rio de Janeiro (ALERJ): deputados no cargo hoje, pelas páginas
públicas do site da ALERJ (não há API nem exportação).

- Lista: a página "Representação Partidária" (www.alerj.rj.gov.br/Deputados/RepresentacaoPartidaria)
  traz os 70 deputados em exercício com partido, foto e o código do perfil.
- Perfil: a ficha de cada deputado dá o nome parlamentar, o telefone e o e-mail do gabinete.

As proposições não entram: o processo legislativo da ALERJ roda num Lotus Notes antigo
(alerjln1.alerj.rj.gov.br) que só mostra as primeiras linhas de cada visão (as chamadas
paginadas são derrubadas pelo servidor) e cuja busca por texto corta em 1.000 resultados
misturando andamentos e despachos. Ver docs/DECISOES.md. Votos, presença e gastos também
não têm publicação em formato aproveitável.

Uma requisição por vez, com pausa. Grava nas mesmas tabelas das outras casas, pela
gravação do conector SAPL.
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

FONTE = "alerj"
SITE = "https://www.alerj.rj.gov.br"
LISTA = SITE + "/Deputados/RepresentacaoPartidaria"
PAUSA = 0.5
CARTAO = re.compile(
    r'<div class="controle_deputado[^"]*">\s*<div class="imagem">\s*'
    r'<a href="/Deputados/PerfilDeputado/(?P<id>\d+)[^"]*"><img src="(?P<foto>[^"]*)"[^>]*></a>'
    r'.*?<div class="partido">(?P<partido>.*?)</div>\s*'
    r'<div class="nome"><a[^>]*>(?P<nome>.*?)</a>',
    re.S,
)


def _limpo(trecho: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", trecho or "")).split())


def _decodificar(conteudo: bytes) -> str:
    """O site declara UTF-8, mas partes antigas vêm em Windows-1252."""
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", errors="replace")


def deputados(pagina: str) -> list[dict[str, str | None]]:
    """Os cartões da lista: id do perfil, nome, partido e foto (sem repetir)."""
    vistos, resultado = set(), []
    for c in CARTAO.finditer(pagina):
        if c.group("id") in vistos:
            continue
        vistos.add(c.group("id"))
        foto = c.group("foto").strip()
        resultado.append(
            {
                "id": c.group("id"),
                "nome": comum.nome_proprio(_limpo(c.group("nome"))),
                "partido": _limpo(c.group("partido")) or None,
                "foto": SITE + foto if foto.startswith("/") else foto or None,
            }
        )
    return resultado


def perfil(pagina: str) -> dict[str, str | None]:
    """Nome parlamentar (com a caixa certa), telefone e e-mail da ficha do deputado."""
    nome = re.search(r'class="descricao">\s*<h1>(.*?)</h1>', pagina, re.S)
    contato = re.search(r"<h2[^>]*>CONTATO</h2>(.*?)</div>", pagina, re.S)
    trecho = contato.group(1) if contato else ""
    email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", trecho)
    telefone = re.search(r"<p>\s*(\(?\d{2}\)?[\s\d.-]{7,}\d)\s*</p>", trecho)
    return {
        "nome": _limpo(nome.group(1)) if nome else None,
        "email": email.group(0).lower() if email else None,
        "telefone": telefone.group(1).strip() if telefone else None,
    }


def coletar() -> dict:
    with comum.criar_cliente() as client:
        lista = deputados(_decodificar(comum._get(client, LISTA, None, 4).content))
        for d in lista:
            time.sleep(PAUSA)
            try:
                ficha = perfil(
                    _decodificar(
                        comum._get(
                            client, f"{SITE}/Deputados/PerfilDeputado/{d['id']}", None, 3
                        ).content
                    )
                )
            except Exception as erro:  # um perfil fora do ar não derruba a lista
                print(f"  perfil {d['id']}: {erro.__class__.__name__}", flush=True)
                ficha = {}
            d.update(
                {k: v for k, v in ficha.items() if v and k != "nome"},
                nome=ficha.get("nome") or d["nome"],
            )
    vereadores = [
        {
            "id_externo": d["id"],
            "nome": d["nome"],
            "nome_completo": None,
            "partido": d["partido"],
            "foto_url": d["foto"],
            "email": d.get("email"),
            "telefone": d.get("telefone"),
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
        "base": SITE + "/Deputados/QuemSao",
        "legislatura": None,
        "vereadores": vereadores,
        "votacoes": [],
        "votos": [],
    }


def executar() -> int:
    casa = coletar()
    if len(casa["vereadores"]) < 60:  # a ALERJ tem 70 cadeiras: lista curta é falha da fonte
        raise ValueError(f"Só {len(casa['vereadores'])} deputados na ALERJ; abortando.")
    with SessionLocal() as session:
        total = sapl.gravar(session, None, casa, uf="RJ")
        session.add(
            FonteIngestao(fonte=FONTE, url=LISTA, arquivo_raw="(não guardado)", registros=total,
                          status="ok", concluido_em=datetime.now(UTC))
        )  # fmt: skip
        session.commit()
    print(f"ALERJ: {total} deputados", flush=True)
    return total


if __name__ == "__main__":
    argparse.ArgumentParser(description=f"Ingestão: {FONTE}").parse_args()
    executar()
