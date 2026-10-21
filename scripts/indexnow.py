#!/usr/bin/env python3
"""Avisa o IndexNow (Bing, Yandex etc.) das URLs do sitemap do Panóptico.

Só biblioteca padrão. Exemplos:
    python scripts/indexnow.py --simular
    python scripts/indexnow.py --padrao /parlamentar/ --padrao '^https://[^/]+/?$'
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

# Pública por definição: o arquivo <chave>.txt no site prova a posse.
CHAVE = "4c18fd44f1bd172d267096252df88142"
ENDPOINT = "https://api.indexnow.org/indexnow"
USER_AGENT = "Panoptico/0.1 (+https://panoptico.social.br; contato@panoptico.social.br)"
LOTE = 10_000


def baixar(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def urls_do_sitemap(site: str) -> list[str]:
    status, corpo = baixar(f"{site.rstrip('/')}/sitemap.xml")
    if status != 200:
        sys.exit(f"Erro: sitemap respondeu {status}")
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", corpo)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", default="https://panoptico.social.br")
    ap.add_argument("--padrao", action="append", default=[], help="regex; repetível; sem = todas")
    ap.add_argument("--simular", action="store_true", help="só conta as URLs, não envia")
    a = ap.parse_args()

    site = a.site.rstrip("/")
    host = urlparse(site).netloc
    urls = urls_do_sitemap(site)
    if a.padrao:
        regs = [re.compile(p) for p in a.padrao]
        urls = [u for u in urls if any(r.search(u) for r in regs)]
    print(f"{len(urls)} URLs para enviar")
    if a.simular:
        return
    if not urls:
        return

    key_url = f"{site}/{CHAVE}.txt"
    status, corpo = baixar(key_url)
    if status != 200 or corpo.strip() != CHAVE:
        sys.exit(
            f"Erro: {key_url} não responde 200 com a chave (status {status}). O deploy já chegou?"
        )

    falhou = False
    for i in range(0, len(urls), LOTE):
        lote = urls[i : i + LOTE]
        corpo_envio = {"host": host, "key": CHAVE, "keyLocation": key_url, "urlList": lote}
        dados = json.dumps(corpo_envio).encode()
        req = urllib.request.Request(
            ENDPOINT,
            data=dados,
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                code, resp = r.status, ""
        except urllib.error.HTTPError as e:
            code, resp = e.code, e.read().decode("utf-8", "replace")[:300]
        if code in (200, 202):
            print(f"Lote {i // LOTE + 1}: {len(lote)} URLs, resposta {code}")
        else:
            print(f"Lote {i // LOTE + 1}: erro {code} {resp}", file=sys.stderr)
            falhou = True
    if falhou:
        sys.exit(1)


if __name__ == "__main__":
    main()
