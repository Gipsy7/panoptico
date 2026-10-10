"""Câmara de Queimada Nova (PI), no site da AOS Software (`/vereadores`, sistema "adtrcloud"):
vereadores em exercício com apelido, nome civil e partido.

O site não tem API; a página `/vereadores` é HTML renderizado no servidor, com um cartão por
vereador: foto com `alt="Foto do(a) vereador(a)<nome civil>"`, o apelido em `<h3>`, o partido
entre parênteses e o link da ficha (`/vereador/<nome-civil>`). O `robots.txt` não existe (404),
nada é proibido. A página lista só quem está no cargo; os cartões já trazem tudo o que
guardamos, então é uma única requisição por câmara.

Fora: projetos, votos e presença (as páginas de matérias são do sistema de processo legislativo,
atrás de login). Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao
eleito do TSE). A outra câmara do fornecedor, Santana do Piauí, usa o Portal Modelo (Plone) e
é lida por `ingestion.camaras.portal_modelo`.
"""

import argparse
import html
import re
from datetime import UTC, datetime
from urllib.parse import urljoin

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.canais import catalogo

FONTE = "aos_camaras"
SISTEMA = "aos"
ACEITA = "text/html,application/xhtml+xml"
LEGISLATURA = ("2025-01-01", "2028-12-31")

CARTAO = re.compile(
    r'<img[^>]*src="([^"]+)"[^>]*alt="Foto do\(a\) vereador\(a\)([^"]*)"[^>]*>\s*'
    r"<h3>(.*?)</h3>\s*<p>\((.*?)\)</p>\s*"
    r'<a href="([^"]*/vereador/[^"]+)"',
    re.S,
)


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def vereadores(pagina: str, base: str) -> list[dict]:
    """Os vereadores dos cartões da página, sem repetir."""
    achados, vistos = [], set()
    for foto, civil, apelido, partido, link in CARTAO.findall(pagina):
        id_externo = sapl.id_curto(link.rstrip("/").rsplit("/", 1)[-1])
        if id_externo in vistos:
            continue
        vistos.add(id_externo)
        nome, completo = _texto(apelido), _texto(civil)
        achados.append(
            {
                "id_externo": id_externo,
                "nome": nome,
                "nome_completo": completo if completo and completo != nome else None,
                "partido": _texto(partido) or None,
                "foto_url": urljoin(base, foto),
                "email": None,
                "telefone": None,
                "titular": True,
                "em_exercicio": True,
                "inicio": LEGISLATURA[0],
                "fim": LEGISLATURA[1],
                "proposicoes_por_tipo": {},
                "projetos": [],
            }
        )
    return achados


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    base = url.rstrip("/") + "/vereadores"
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA
        pagina = comum.get_bytes(client, base).decode("utf-8", "replace")
    return {"base": base, "legislatura": None, "vereadores": vereadores(pagina, base)}


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
                url="sites das câmaras do catálogo data/canais_curados.csv (AOS Software)",
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
