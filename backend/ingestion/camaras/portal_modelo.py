"""Câmaras municipais no Portal Modelo do Interlegis (Plone) cujos parlamentares estão cadastrados
no próprio portal: Imbuia (SC), Santana do Piauí (PI), Vila Flores (RS) e Campo Novo de Rondônia
(RO). Vereadores em exercício com nome (apelido e nome civil) e partido.

O portal é HTML renderizado no servidor, sem API de dados abertos. A lista de parlamentares
(`/processo-legislativo/parlamentares`) tem dois jeitos de aparecer:

- com um seletor de legislaturas (`<select id="legislatures">`, a atual marcada "(Atual)"): a
  lista vem de `@@legislature-members?legislature=<id>`, com a seção "Ativos" (um cartão por
  pessoa, com apelido e partido) e a seção "Inativos", que fica de fora (Imbuia);
- sem seletor, como pasta de conteúdos com uma página por parlamentar publicada na legislatura
  atual (Santana do Piauí).

Dois jeitos a mais, para portais em que a lista de parlamentares é a do SAPL parado:

- a pasta `/processo-legislativo/legislaturas` com uma página por legislatura, a atual com
  "(Atual)" no título e a tabela de membros (nome completo, nome, partido, situação), caso de
  Vila Flores;
- a capa da legislatura de 2025-2028 em `/institucional/legislatura/<id>/capa` (um bloco
  `<div class="vereador">` por pessoa, com nome civil abreviado e partido), caso de Campo Novo
  de Rondônia, em que o título da ficha é o nome de urna.

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

import httpx

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
LEGISLATURAS = "/processo-legislativo/legislaturas"
CAPAS = "/institucional/legislatura"

ATUAL = re.compile(r'<option value="([0-9a-f]+)"[^>]*>[^<]*\(Atual\)', re.I)
CARTAO = re.compile(
    r'<li class="photoAlbumEntry"[^>]*>\s*<a href="([^"]+)"[^>]*>.*?'
    r'<span itemprop="name">(.*?)</span>\s*-\s*<span class="party"[^>]*>(.*?)</span>',
    re.S,
)
ITEM_DA_PASTA = re.compile(r'<a href="([^"]+/parlamentares/[^"/]+)" class="summary url">(.*?)</a>')
NOME_CIVIL = re.compile(r'id="form-widgets-full_name"[^>]*>(.*?)</span>', re.S)
PARTIDO = re.compile(r'itemprop="memberOf">(.*?)</span>', re.S)
LINK_LEGISLATURA = re.compile(r'href="[^"]*/legislaturas/([^"/]+)"')
TITULO = re.compile(r'<h1 class="documentFirstHeading"[^>]*>(.*?)</h1>', re.S)
LINHA_MEMBRO = re.compile(
    r"<tr>\s*<td[^>]*>\s*<a href=\"([^\"]+)\"[^>]*>(.*?)</a>\s*</td>(.*?)</tr>", re.S
)
CELULA = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
CAPA_2025 = re.compile(r'href="([^"]*/legislatura/[^"/]+)"\s+title="2025-2028"')
BLOCO_CAPA = re.compile(
    r'<div class="vereador">\s*<a [^>]*?href="([^"]+)".*?<strong>(.*?)</strong>'
    r"\s*<br\s*/?>\s*<i>\((.*?)\)</i>",
    re.S,
)


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


def membros_da_legislatura(pagina: str) -> list[dict]:
    """Vereadores da página de uma legislatura que traz "(Atual)" no título, só os 'Ativo'."""
    achado = TITULO.search(pagina)
    if not achado or "(Atual)" not in achado[1]:
        return []
    membros = []
    for link, completo, resto in LINHA_MEMBRO.findall(pagina):
        celulas = [_texto(c) for c in CELULA.findall(resto)]
        if len(celulas) < 3 or celulas[2].lower() != "ativo":
            continue
        apelido = celulas[0] or _texto(completo)
        membros.append(_registro(link, apelido, _texto(completo), celulas[1]))
    return membros


def blocos_da_capa(pagina: str) -> list[tuple[str, str, str]]:
    """(link da ficha, nome civil abreviado, partido) de cada bloco da capa da legislatura."""
    return [
        (link, _texto(nome), _texto(partido)) for link, nome, partido in BLOCO_CAPA.findall(pagina)
    ]


def _registro(link: str, apelido: str, civil: str, partido: str) -> dict:
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


def vereador(link: str, apelido: str, partido_da_lista: str, ficha: str) -> dict:
    achado_civil = NOME_CIVIL.search(ficha)
    civil = _texto(achado_civil[1]) if achado_civil else ""
    achado_partido = PARTIDO.search(ficha)
    partido = (_texto(achado_partido[1]) if achado_partido else "") or partido_da_lista
    return _registro(link, apelido, civil, partido)


def _pela_pasta_de_legislaturas(base: str, pagina) -> list[dict]:
    """Vila Flores: a legislatura "(Atual)" da pasta de legislaturas, com a tabela de membros."""
    try:
        indice = pagina(base + LEGISLATURAS)
    except httpx.HTTPStatusError:
        return []
    for slug in dict.fromkeys(LINK_LEGISLATURA.findall(indice)):
        if slug in ("RSS", "atom.xml", "rss.xml"):
            continue
        membros = membros_da_legislatura(pagina(f"{base}{LEGISLATURAS}/{slug}"))
        if membros:
            return membros
    return []


def _pela_capa(base: str, pagina) -> list[dict]:
    """Campo Novo de Rondônia: a capa da legislatura marcada 2025-2028 e a ficha de cada um."""
    try:
        indice = pagina(base + CAPAS)
    except httpx.HTTPStatusError:
        return []
    achado = CAPA_2025.search(indice)
    if not achado:
        return []
    vereadores = []
    for link, civil, partido in blocos_da_capa(pagina(achado[1] + "/capa")):
        titulo = TITULO.search(pagina(link))
        apelido = _texto(titulo[1]) if titulo else civil
        vereadores.append(_registro(link, apelido, civil, partido))
    return vereadores


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    base = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA

        def pagina(endereco: str) -> str:
            time.sleep(PAUSA)
            return comum.get_bytes(client, endereco).decode("utf-8", "replace")

        try:
            lista = pagina(base + LISTA)
        except httpx.HTTPStatusError as erro:
            if erro.response.status_code != 404:
                raise
            lista = ""  # portal sem essa pasta (Campo Novo de Rondônia): cai na capa da legislatura
        atual = legislatura_atual(lista)
        if atual:
            pessoas = ativos(pagina(f"{base}{LISTA}/@@legislature-members?legislature={atual}"))
        else:
            pessoas = itens_da_pasta(lista)
        vereadores = [
            vereador(link, nome, partido, pagina(link)) for link, nome, partido in pessoas
        ]
        if not vereadores:
            vereadores = _pela_pasta_de_legislaturas(base, pagina)
        if not vereadores:
            vereadores = _pela_capa(base, pagina)
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
