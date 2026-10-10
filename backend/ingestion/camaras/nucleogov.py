"""Câmaras municipais com portal WordPress da Nucleogov / 7Focus (Pirenópolis e Campos Belos, no
GO; Cariri do Tocantins, Figueirópolis e Santa Rita do Tocantins, no TO): vereadores em exercício
com nome e partido.

O portal não tem API de dados abertos (o `wp-json` não expõe o tipo `vereadores`), mas o HTML é
renderizado no servidor e o robots.txt só proíbe `/wp-admin/`, `/wp-includes/` e `/*.html$`, com
`Crawl-Delay: 5` (respeitado: cinco segundos entre requisições). A página inicial traz um link
`/vereador/<slug>/` por vereador em exercício (o menu "Vereadores" e os cartões da Mesa); a
ficha de cada um tem o nome e o partido, em dois leiautes de tema:

- tema com `<h1>` e campos `<span class="label">Partido:</span><span>PSDB</span>`
  (Pirenópolis, Cariri, Figueirópolis);
- tema "araguaia" (Santa Rita) com título `Ver. Fulano`, e os campos "nome civil" e "partido"
  em blocos `wp-block-nwe-acf`.

O partido é o que o site informa e pode estar desatualizado (Cariri ainda mostra "DEM", extinto
em 2022). Projetos, votos e presença ficam no portal de transparência de cada câmara
(`acessoainformacao.<câmara>`), sem formato estruturado reconhecido; por isso a câmara entra só
com os vereadores. Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao
eleito do TSE).
"""

import argparse
import html
import re
import time
from datetime import UTC, datetime
from urllib.parse import urljoin

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.canais import catalogo

FONTE = "nucleogov_camaras"
SISTEMA = "nucleogov"
PAUSA = 5.0  # o Crawl-Delay do robots.txt dos portais
ACEITA = "text/html,application/xhtml+xml"
LEGISLATURA = ("2025-01-01", "2028-12-31")

LINK_VEREADOR = re.compile(r'href="(https?://[^"]+?/vereador/[^"/]+/?)"')
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
TITULO = re.compile(r"<h2[^>]*wp-block-post-title[^>]*>(.*?)</h2>", re.S)
CARGO = re.compile(r"<div class=\"header-content\">\s*<span>(.*?)</span>", re.S)
FOTO = re.compile(r'<a[^>]*class="header"[^>]*>\s*<img src="([^"]+)"', re.S)
PREFIXO_TITULO = re.compile(r"^Ver[ªa]?\.\s*", re.I)  # "Ver. Fulano", "Verª. Fulana", "Ver.Fulano"


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def sigla(partido: str) -> str:
    """O partido pode vir por extenso ("Partido Democrático Trabalhista – PDT"): fica a sigla."""
    partes = [p.strip() for p in re.split(r"\s+[–-]\s+", partido)]
    siglas = [p for p in partes if p and p == p.upper() and len(p) <= 15]
    return (siglas[0] if siglas else partido)[:30]


def links_da_pagina_inicial(pagina: str) -> list[str]:
    """Os links das fichas, sem repetir e na ordem da página."""
    return list(dict.fromkeys(m.rstrip("/") + "/" for m in LINK_VEREADOR.findall(pagina)))


def _campo(pagina: str, rotulo: str) -> str:
    """O valor de um campo da ficha, nos dois leiautes (rótulo com ou sem os dois-pontos)."""
    r = re.escape(rotulo)
    for padrao in (
        rf'<span class="label">\s*{r}:?\s*</span>\s*<span>(.*?)</span>',
        rf"<p[^>]*>\s*{r}\s*</p>\s*<div[^>]*wp-block-nwe-acf[^>]*>(.*?)</div>",
    ):
        achado = re.search(padrao, pagina, re.S | re.I)
        if achado:
            return _texto(achado[1])
    return ""


def ficha(pagina: str, url: str) -> dict | None:
    """O vereador de uma ficha, ou None se a página não tem nome."""
    h1 = H1.search(pagina)
    titulo = TITULO.search(pagina)
    civil = _campo(pagina, "nome civil")
    if h1:
        nome = _texto(h1[1])
    elif titulo:
        nome = _texto(titulo[1])
    else:
        return None
    nome = PREFIXO_TITULO.sub("", nome)
    if not nome:
        return None
    cargo = CARGO.search(pagina)
    cargo = _texto(cargo[1]).upper() if cargo else ""
    foto = FOTO.search(pagina)
    return {
        "id_externo": sapl.id_curto(url.rstrip("/").rsplit("/", 1)[-1]),
        "nome": nome,
        "nome_completo": civil if civil and civil != nome else None,
        "partido": sigla(_campo(pagina, "partido")) or None,
        "foto_url": urljoin(url, foto[1]) if foto else None,
        "email": None,
        "telefone": None,
        "titular": "SUPLENTE" not in cargo,
        "em_exercicio": "LICENCIAD" not in cargo,
        "inicio": LEGISLATURA[0],
        "fim": LEGISLATURA[1],
        "proposicoes_por_tipo": {},
        "projetos": [],
    }


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    home = url.rstrip("/") + "/"
    base = home + "vereador/"  # onde ficam as fichas; também diz de qual conector a câmara veio
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA

        def pagina(endereco: str) -> str:
            time.sleep(PAUSA)
            return comum.get_bytes(client, endereco).decode("utf-8", "replace")

        links = links_da_pagina_inicial(pagina(home))
        fichas = [ficha(pagina(link), link) for link in links]
    return {"base": base, "legislatura": None, "vereadores": [v for v in fichas if v]}


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
                url="portais das câmaras do catálogo data/canais_curados.csv (Nucleogov / 7Focus)",
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
