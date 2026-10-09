"""Reconhecimento (descartável): para as câmaras cujo SAPL parou na legislatura 2021–2024,
abre a página da câmara (uma requisição por câmara) e anota para onde apontam os links
legislativos (proposições, matérias, sessões, vereadores, leis). Serve para descobrir o
sistema novo de cada uma e agrupar por fornecedor.

Uso: python -m scripts.reconhecer.sapl_parado > saida.csv
"""

import csv
import re
import sys
import time
from collections import Counter
from urllib.parse import urljoin, urlparse

import httpx

from ingestion.canais.catalogo import ler
from ingestion.comum import USER_AGENT

PALAVRAS = re.compile(r"proposi|materia|legisla|sess(ao|oes)|vereador|leis|pauta|votac", re.I)
ASSINATURAS = [
    ("sapl", re.compile(r"sapl", re.I)),
    ("siscam", re.compile(r"siscam", re.I)),
    ("ipm (atende.net)", re.compile(r"atende\.net", re.I)),
    ("betha", re.compile(r"betha", re.I)),
    ("legisweb", re.compile(r"legisweb", re.I)),
    ("splegis", re.compile(r"splegis|spl\.", re.I)),
    ("sino", re.compile(r"sino\.|siteseguro", re.I)),
    ("kingpage", re.compile(r"kingpage", re.I)),
    ("leis municipais", re.compile(r"leismunicipais", re.I)),
    ("camara.app / instar", re.compile(r"instar|camara\.app", re.I)),
    ("smarapd", re.compile(r"smarapd", re.I)),
    ("4r", re.compile(r"4r\.com|4rsistemas", re.I)),
    ("ecrie", re.compile(r"ecrie", re.I)),
    ("portalfacil", re.compile(r"portalfacil", re.I)),
]


def main() -> None:
    catalogo = ler()
    sapl_por_ibge = {c["municipio_ibge"]: c["url"] for c in catalogo if c["tipo"] == "sapl"}
    camara_por_ibge = {c["municipio_ibge"]: c["url"] for c in catalogo if c["tipo"] == "camara"}
    paradas = [linha.strip() for linha in sys.stdin if linha.strip()]
    saida = csv.writer(sys.stdout)
    saida.writerow(["sapl", "pagina", "status", "sistema", "hosts_legislativos"])
    contagem: Counter = Counter()
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as c:
        for host in paradas:
            ibge = next((i for i, u in sapl_por_ibge.items() if host in u), None)
            pagina = camara_por_ibge.get(ibge) or "https://www." + host.removeprefix("sapl.")
            time.sleep(0.5)
            try:
                resposta = c.get(pagina)
                html = resposta.text
                status = resposta.status_code
            except httpx.HTTPError as erro:
                saida.writerow([host, pagina, erro.__class__.__name__, "", ""])
                continue
            links = {urljoin(str(resposta.url), h) for h in re.findall(r'href="([^"#]+)"', html)}
            legislativos = [u for u in links if PALAVRAS.search(u)]
            hosts = Counter(urlparse(u).netloc for u in legislativos)
            texto = html + " ".join(legislativos)
            sistema = next((n for n, p in ASSINATURAS if p.search(texto) and n != "sapl"), None)
            if sistema is None and re.search(r"sapl", texto, re.I):
                sistema = "sapl (outro endereço?)"
            contagem[sistema or "?"] += 1
            saida.writerow([host, pagina, status, sistema or "",
                            " ".join(f"{h}:{n}" for h, n in hosts.most_common(3))])  # fmt: skip
    print(dict(contagem), file=sys.stderr)


if __name__ == "__main__":
    main()
