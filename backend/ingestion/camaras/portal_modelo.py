"""Câmaras municipais no Portal Modelo do Interlegis (Plone) cujos parlamentares estão cadastrados
no próprio portal: Imbuia (SC) e Santana do Piauí (PI). Vereadores em exercício com nome
(apelido e nome civil) e partido.

O portal é HTML renderizado no servidor, sem API de dados abertos. A lista de parlamentares
(`/processo-legislativo/parlamentares`) tem dois jeitos de aparecer:

- com um seletor de legislaturas (`<select id="legislatures">`, a atual marcada "(Atual)"): a
  lista vem de `@@legislature-members?legislature=<id>`, com a seção "Ativos" (um cartão por
  pessoa, com apelido e partido) e a seção "Inativos", que fica de fora (Imbuia);
- sem seletor, como pasta de conteúdos com uma página por parlamentar publicada na legislatura
  atual (Santana do Piauí).

A ficha de cada um traz o nome civil (`form-widgets-full_name`) e o partido (`memberOf`).
Câmaras do mesmo portal que ainda mostram a lista vazia (Carolina, no MA: seletor sem
legislaturas, lista que dependia do SAPL parado) não têm o que ler e ficam de fora. Uma
requisição por vez, com pausa. Projetos, votos e presença não existem no portal. Grava nas
mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao eleito do TSE).
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
from ingestion.canais import catalogo

FONTE = "portal_modelo_camaras"
SISTEMA = "portal_modelo"
PAUSA = 1.0
ACEITA = "text/html,application/xhtml+xml"
LEGISLATURA = ("2025-01-01", "2028-12-31")
LISTA = "/processo-legislativo/parlamentares"

ATUAL = re.compile(r'<option value="([0-9a-f]+)"[^>]*>[^<]*\(Atual\)', re.I)
CARTAO = re.compile(
    r'<li class="photoAlbumEntry"[^>]*>\s*<a href="([^"]+)"[^>]*>.*?'
    r'<span itemprop="name">(.*?)</span>\s*-\s*<span class="party"[^>]*>(.*?)</span>',
    re.S,
)
ITEM_DA_PASTA = re.compile(r'<a href="([^"]+/parlamentares/[^"/]+)" class="summary url">(.*?)</a>')
NOME_CIVIL = re.compile(r'id="form-widgets-full_name"[^>]*>(.*?)</span>', re.S)
PARTIDO = re.compile(r'itemprop="memberOf">(.*?)</span>', re.S)


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def legislatura_atual(pagina: str) -> str | None:
    achado = ATUAL.search(pagina)
    return achado[1] if achado else None


def ativos(pagina: str) -> list[tuple[str, str, str]]:
    """(link, apelido, partido) de quem está na seção 'Ativos' do `@@legislature-members`."""
    ate = pagina.find("<h2>Inativos</h2>")
    trecho = pagina[: ate if ate > 0 else len(pagina)]
    return [(link, _texto(nome), _texto(partido)) for link, nome, partido in CARTAO.findall(trecho)]


def itens_da_pasta(pagina: str) -> list[tuple[str, str, str]]:
    """(link, apelido, partido vazio) dos parlamentares publicados na pasta, sem repetir."""
    vistos = dict.fromkeys((link, _texto(nome), "") for link, nome in ITEM_DA_PASTA.findall(pagina))
    return list(vistos)


def vereador(link: str, apelido: str, partido_da_lista: str, ficha: str) -> dict:
    achado_civil = NOME_CIVIL.search(ficha)
    civil = _texto(achado_civil[1]) if achado_civil else ""
    achado_partido = PARTIDO.search(ficha)
    partido = (_texto(achado_partido[1]) if achado_partido else "") or partido_da_lista
    return {
        "id_externo": sapl.id_curto(link.rstrip("/").rsplit("/", 1)[-1]),
        "nome": apelido,
        "nome_completo": civil if civil and civil != apelido else None,
        "partido": partido or None,
        "foto_url": None,
        "email": None,
        "telefone": None,
        "titular": True,
        "em_exercicio": True,
        "inicio": LEGISLATURA[0],
        "fim": LEGISLATURA[1],
        "proposicoes_por_tipo": {},
        "projetos": [],
    }


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    base = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA

        def pagina(endereco: str) -> str:
            time.sleep(PAUSA)
            return comum.get_bytes(client, endereco).decode("utf-8", "replace")

        lista = pagina(base + LISTA)
        atual = legislatura_atual(lista)
        if atual:
            pessoas = ativos(pagina(f"{base}{LISTA}/@@legislature-members?legislature={atual}"))
        else:
            pessoas = itens_da_pasta(lista)
        vereadores = [
            vereador(link, nome, partido, pagina(link)) for link, nome, partido in pessoas
        ]
    return {"base": base + LISTA, "legislatura": None, "vereadores": vereadores}


def executar(limite: int | None = None) -> int:
    camaras = [
        (c["municipio_ibge"], c["url"])
        for c in catalogo.ler()
        if c["tipo"] == "sistema_legislativo" and c["sistema"] == SISTEMA
    ]
    camaras = camaras[:limite] if limite else camaras
    total, falhas = 0, 0
    for ibge, url in camaras:
        try:
            camara = coletar(url)
            if not camara["vereadores"]:
                raise ValueError("nenhum vereador encontrado")
            with SessionLocal() as session:
                total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {url}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="portais das câmaras do catálogo data/canais_curados.csv (Portal Modelo)",
                arquivo_raw="(não guardado)",
                registros=total,
                status="ok",
                concluido_em=datetime.now(UTC),
            )
        )
        session.commit()
    print(f"{len(camaras)} câmaras, {falhas} com falha, {total} vereadores", flush=True)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--limite", type=int, help="Só as N primeiras câmaras (teste)")
    args = parser.parse_args()
    executar(args.limite)
