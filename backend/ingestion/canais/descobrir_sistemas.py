"""Descoberta do site e do sistema legislativo das câmaras que o catálogo ainda não tem.

Parte de `data/cidades_sem_canal.csv` (cidades sem nenhum canal) e, para cada uma:
1. monta os endereços prováveis da câmara (`camara<cidade>.<uf>.gov.br`, `<cidade>.<uf>.leg.br`,
   `cm...`, `camaramunicipal...`, `.org.br`, `.com.br`, com e sem `www.`), consulta o DNS (sem
   tocar no site) e só abre os que existem;
2. respeita o `robots.txt` do servidor (quem veda robôs fica como "bloqueado", sem tentar de
   outro jeito) e faz uma requisição por vez por servidor, com identificação do Panóptico;
3. aceita a página que é da Câmara Municipal da cidade (domínio com o nome e prefixo
   `camara`/`cm` ou nome da cidade e "câmara" no texto);
4. lê a assinatura do fornecedor no HTML (rodapé, scripts, gerador, links) e confere se o
   SAPL (`/api/`) responde;
5. grava o resultado bruto em `data/raw/descoberta_sistemas/` e o CSV
   `data/cidades_sem_canal_sistemas.csv` (ibge, uf, cidade, url, sistema, situacao,
   evidencia). A situação é `aberto` (há leitor e dado público), `bloqueado` (robots veda,
   captcha ou 403 ao robô) ou `desconhecido` (site achado, sistema ou dado sem leitor).

    python -m ingestion.canais.descobrir_sistemas [--limite N] [--uf SC MG] [--de-raw]
"""

import argparse
import asyncio
import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.config import BACKEND_DIR
from ingestion.canais.segunda_varredura import ESTACIONADO, SEM_CANAL, variacoes_slug
from ingestion.canais.varredura import slugs
from ingestion.comum import USER_AGENT, chave_nome

RAIZ = BACKEND_DIR.parent
RAW = BACKEND_DIR / "data" / "raw" / "descoberta_sistemas"
SAIDA = RAIZ / "data" / "cidades_sem_canal_sistemas.csv"
COLUNAS = ["ibge", "uf", "cidade", "url", "sistema", "situacao", "evidencia"]

# Assinatura no HTML (minúsculas) -> sistema. A ordem importa: o primeiro que casa vence.
ASSINATURAS: list[tuple[str, re.Pattern]] = [
    ("cittatec", re.compile(r"cittatec\.com\.br|citta conecta")),
    ("portal_php", re.compile(r"papelvereador\.php")),
    ("cr2", re.compile(r"portalcr2\.com\.br|cr2\.site")),
    ("nucleogov", re.compile(r"nucleogov|7focus")),
    ("aos", re.compile(r"adtrcloud|aossoftware")),
    ("betha", re.compile(r"betha\.cloud|bethacloud|betha\.com\.br")),
    ("nexlegis", re.compile(r"nexlegis")),
    ("digitaliza", re.compile(r"servicosaocidadao\.net\.br")),
    ("siscam", re.compile(r"siscam\.com\.br")),
    ("camarasempapel", re.compile(r"camarasempapel|nopapercloud")),
    ("instar", re.compile(r"instar\.com\.br")),
    ("legislador", re.compile(r"legislador\.com\.br")),
    ("megasoft", re.compile(r"megasoft")),
    ("sgpcloud", re.compile(r"sgpcloud\.net")),
    ("sistemalegislativo", re.compile(r"sistemalegislativo\.com\.br")),
    ("publicsoft", re.compile(r"publicsoft")),
    ("cespro", re.compile(r"cespro\.com\.br")),
    ("ingadigital", re.compile(r"ingadigital")),
    ("dofem", re.compile(r"dofem\.com\.br")),
    ("sudoeste", re.compile(r"sudoesteinformatica")),
    ("ipm", re.compile(r"atende\.net|e-solution|ipm\.com\.br")),
    ("portaldeservicos", re.compile(r"portaldeservicos\.app")),
    ("webline", re.compile(r"webline")),
    ("governoweb", re.compile(r"gwlegis\.com\.br|governoweb\.com\.br|gps-legislativo")),
    ("abase", re.compile(r"abase\.com\.br|adentro\.com\.br")),
    ("webservicesistemas", re.compile(r"webservicesistemas\.com\.br")),
    ("sts", re.compile(r"stsinformatica\.com\.br|sts-gestao")),
    ("portalfacil", re.compile(r"portalfacil\.com\.br|actcon\.com\.br|actcon\.net")),
    ("icamaras", re.compile(r"icamaras\.com\.br|visaoi\.com\.br")),
    ("siplan", re.compile(r"siplanweb\.com\.br")),
    ("nuvemlegislativa", re.compile(r"nuvemlegislativa\.com\.br")),
    ("portal_do_municipio", re.compile(r"<title>portal do munic")),
    ("plone", re.compile(r'content="plone|generator" content="plone|portal_css/|\+\+resource\+\+')),
    ("wix", re.compile(r"wixstatic\.com|wix\.com")),
    ("fiorilli", re.compile(r"fiorilli")),
    ("elotech", re.compile(r"elotech")),
    ("dominio", re.compile(r"dominiosistemas|dominio\.com\.br")),
    ("agili", re.compile(r"agilicloud|agili\.com\.br")),
    ("proweb", re.compile(r"proweb")),
    ("legislativo_net", re.compile(r"legislativo\.net|camaraleg\.com\.br|sislegis")),
]
SISTEMAS_CONHECIDOS = {nome for nome, _ in ASSINATURAS} | {"sapl"}
RODAPE = re.compile(
    r"(?:desenvolvido|criado|mantido|hospedado|powered)\s+(?:por|by)\s*:?\s*([^<|\n]{3,60})",
    re.I,
)
# Captcha ou desafio de robô na página: vira "bloqueado", nunca se contorna.
CAPTCHA = re.compile(r"cf-challenge|just a moment|attention required|"
                     r"verifique que voc[eê] [eé] humano|sgcaptcha", re.I)  # fmt: skip
RECAPTCHA = re.compile(r"g-recaptcha|recaptcha/api|hcaptcha", re.I)  # em formulário: só anotado
SUFIXOS = (".{uf}.leg.br", ".{uf}.gov.br", ".org.br", ".com.br")
PREFIXOS = ("camara", "cm", "camaramunicipal", "camaramunicipalde")


def hosts_candidatos(nome: str, uf: str) -> list[str]:
    """Endereços prováveis da câmara, do mais ao menos provável."""
    uf = uf.lower()
    ordem: list[str] = []
    for s in dict.fromkeys(slugs(nome) + variacoes_slug(nome)):
        ordem += [f"{s}.{uf}.leg.br"]
        for p in PREFIXOS:
            for suf in SUFIXOS:
                ordem.append(f"{p}{s}{suf.format(uf=uf)}")
        ordem.append(f"camara.{s}.{uf}.gov.br")
        ordem.append(f"camara{s}{uf}.com.br")
    return list(dict.fromkeys(ordem))


def sistema_do_robots(texto: str) -> tuple[str, str]:
    """O robots.txt que veda tudo aos demais robôs ainda diz, nas regras dos buscadores, quais
    pastas o sistema tem (`/softcam/`...): isso identifica o fornecedor sem abrir o site."""
    pastas = list(dict.fromkeys(re.findall(r"(?im)^disallow:\s*(/[a-z0-9_-]+/?)\s*$", texto)))
    baixo = texto.lower()
    sistema = "softcam" if "/softcam/" in baixo else ""
    return sistema, (f"; pastas citadas: {' '.join(pastas[:6])}" if pastas else "")


def forte(host: str, nome: str, uf: str) -> bool:
    """O próprio domínio diz: câmara/cm + nome da cidade + estado (ou .leg.br da cidade)."""
    host = host.removeprefix("www.")
    uf = uf.lower()
    cidade = {s.replace("-", "") for s in slugs(nome) + variacoes_slug(nome)}
    base = host.split(".")[0].replace("-", "")
    if host.endswith(f".{uf}.leg.br") and base in cidade:
        return True
    if not (host.endswith(f".{uf}.gov.br") or host.endswith(f".{uf}.leg.br")):
        return False
    return any(base == p + c or base == p + "de" + c for p in PREFIXOS for c in cidade) or (
        host.startswith("camara.") and host.split(".")[1].replace("-", "") in cidade
    )


def e_da_cidade(html: str, nome: str, uf: str, host: str) -> bool:
    """Página com o nome da cidade e "câmara" (domínio fraco) ou domínio forte e não parado."""
    texto = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html[:300_000], flags=re.S | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    if len(texto.strip()) < 600 and ESTACIONADO.search(texto):
        return False
    titulo = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    titulo = chave_nome(titulo.group(1)) if titulo else ""
    if ESTACIONADO.search(titulo):
        return False
    if forte(host, nome, uf):
        return True
    chave = f" {chave_nome(texto)} "
    if f" {chave_nome(nome)} " not in chave or " CAMARA " not in f" {titulo} {chave[:4000]} ":
        return False
    return f".{uf.lower()}." in host or bool(re.search(rf"\b{uf}\b", texto))


def assinatura(html: str, host: str, cabecalhos: dict) -> tuple[str, str]:
    """(sistema, evidencia) pelo HTML e pelos cabeçalhos; ('', '') se nada casou."""
    baixo = html.lower()
    for nome, padrao in ASSINATURAS:
        if achado := padrao.search(baixo):
            return nome, f'"{achado.group(0)[:40]}" no HTML'
    gerador = re.search(
        r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html, re.I
    )
    if gerador:
        return "gerador:" + gerador.group(1)[:30].strip(), "meta generator"
    if rodape := RODAPE.search(html):
        return "rodape:" + " ".join(rodape.group(1).split())[:40], "rodapé do site"
    if "wp-content" in baixo:
        return "wordpress", "wp-content no HTML"
    if "joomla" in baixo:
        return "joomla", "joomla no HTML"
    return "", ""


class Descoberta:
    def __init__(self, conexoes: int = 48, tempo: float = 12.0, pausa: float = 0.4) -> None:
        self.limite = asyncio.Semaphore(conexoes)
        self.pausa = pausa
        self.trava_ip: dict[str, asyncio.Lock] = {}
        self.ips: dict[str, str] = {}
        self.robots: dict[str, RobotFileParser | None | str] = {}
        self.robots_texto: dict[str, str] = {}
        self.cliente = httpx.AsyncClient(
            timeout=httpx.Timeout(tempo),
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"},
            follow_redirects=True,
            verify=False,  # muitos sites municipais têm certificado vencido ou incompleto
        )

    async def fechar(self) -> None:
        await self.cliente.aclose()

    async def ip(self, host: str) -> str:
        if host not in self.ips:
            try:
                info = await asyncio.get_running_loop().getaddrinfo(host, 443)
                self.ips[host] = info[0][4][0]
            except OSError:
                self.ips[host] = ""
        return self.ips[host]

    async def get(self, url: str) -> httpx.Response | None:
        host = urlparse(url).hostname or ""
        ip = await self.ip(host)
        if not ip:
            return None
        trava = self.trava_ip.setdefault(ip, asyncio.Lock())
        async with trava, self.limite:
            try:
                return await self.cliente.get(url)
            except (httpx.HTTPError, UnicodeDecodeError, ValueError):
                return None
            finally:
                await asyncio.sleep(self.pausa)

    async def permitido(self, host: str, caminho: str = "/") -> bool:
        """False se o robots.txt veda o caminho ao nosso robô (ou a qualquer robô)."""
        if host not in self.robots:
            r = await self.get(f"https://{host}/robots.txt")
            regras = None
            if (
                r is not None
                and r.status_code == 200
                and "html" not in r.headers.get("content-type", "")
            ):
                regras = RobotFileParser()
                regras.parse(r.text.splitlines())
            self.robots[host] = regras
            self.robots_texto[host] = r.text[:6000] if regras is not None else ""
        regras = self.robots[host]
        return regras is None or regras.can_fetch(USER_AGENT, caminho)  # type: ignore[union-attr]

    async def e_sapl(self, base: str) -> bool:
        r = await self.get(f"{base}api/parlamentares/parlamentar/?page_size=1")
        return r is not None and r.status_code == 200 and "results" in r.text[:2000]

    async def cidade(self, ibge: str, nome: str, uf: str) -> dict:
        base = {"ibge": ibge, "uf": uf, "cidade": nome}
        todos = hosts_candidatos(nome, uf)
        ips = await asyncio.gather(*(self.ip(h) for h in todos))
        hosts = [h for h, ip in zip(todos, ips, strict=True) if ip]
        bloqueio: dict | None = None
        for host in hosts:
            if not await self.permitido(host):
                sistema, citados = sistema_do_robots(self.robots_texto.get(host, ""))
                bloqueio = bloqueio or {
                    **base,
                    "url": f"https://{host}/",
                    "sistema": sistema,
                    "situacao": "bloqueado",
                    "evidencia": "robots.txt veda robôs (User-agent: * Disallow: /)" + citados,
                }
                continue
            r = await self.get(f"https://{host}/")
            if r is None:
                r = await self.get(f"http://{host}/")
            if r is None:
                continue
            final = urlparse(str(r.url)).hostname or host
            if not final.endswith(".br"):
                continue
            tipo = r.headers.get("content-type", "")
            if r.status_code in (401, 403, 429) and forte(host, nome, uf):
                bloqueio = bloqueio or {
                    **base,
                    "url": f"https://{host}/",
                    "sistema": "",
                    "situacao": "bloqueado",
                    "evidencia": f"HTTP {r.status_code} ao robô"
                    + f" (Server: {r.headers.get('server', '?')})",
                }
                continue
            if r.status_code != 200 or "html" not in tipo:
                continue
            html = r.text[:400_000]
            if "suspendedpage" in str(r.url) or not e_da_cidade(html, nome, uf, final):
                continue
            sistema, evidencia = assinatura(html, final, dict(r.headers))
            situacao = "desconhecido"
            if CAPTCHA.search(html):
                situacao = "bloqueado"
                evidencia = (evidencia + "; " if evidencia else "") + "desafio de robô na página"
            elif RECAPTCHA.search(html):
                evidencia = (evidencia + "; " if evidencia else "") + "reCAPTCHA na página"
            sapl = f"https://sapl.{final.removeprefix('www.')}/"
            if await self.ip(f"sapl.{final.removeprefix('www.')}") and await self.e_sapl(sapl):
                return {
                    **base,
                    "url": sapl,
                    "sistema": "sapl",
                    "situacao": "aberto",
                    "evidencia": "API /api/ do SAPL responde",
                }
            return {
                **base,
                "url": str(r.url),
                "sistema": sistema,
                "situacao": situacao,
                "evidencia": evidencia or "nenhuma assinatura de fornecedor",
            }
        return bloqueio or {
            **base,
            "url": "",
            "sistema": "",
            "situacao": "desconhecido",
            "evidencia": f"nenhum dos {len(hosts)} domínios candidatos com site da câmara",
        }


def ler_cidades(uf: list[str] | None = None) -> list[tuple[str, str, str]]:
    with SEM_CANAL.open(encoding="utf-8", newline="") as f:
        linhas = [(r["ibge"], r["municipio"], r["uf"]) for r in csv.DictReader(f)]
    return [m for m in linhas if not uf or m[2] in uf]


async def varrer(
    cidades: list[tuple[str, str, str]], conexoes: int, de_raw: bool, refazer: str | None = None
) -> list[dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    d = Descoberta()
    sem = asyncio.Semaphore(conexoes)
    feitos = 0

    async def uma(m: tuple[str, str, str]) -> dict:
        nonlocal feitos
        arquivo = RAW / f"{m[0]}.json"
        async with sem:
            try:
                if de_raw and arquivo.exists():
                    antigo = json.loads(arquivo.read_text(encoding="utf-8"))
                    sem_sistema = (
                        antigo["url"] and antigo["sistema"].split(":")[0] not in SISTEMAS_CONHECIDOS
                    )
                    if not (
                        (refazer == "bloqueados" and antigo["situacao"] == "bloqueado")
                        or (
                            refazer == "sem-sistema"
                            and antigo["situacao"] != "bloqueado"
                            and sem_sistema
                        )
                    ):
                        return antigo
                r = await d.cidade(*m)
                r["verificado_em"] = date.today().isoformat()
                arquivo.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                return r
            except Exception as erro:  # um site estranho não derruba a varredura
                print(f"  {m[1]}/{m[2]}: {erro.__class__.__name__}: {str(erro)[:100]}")
                return {
                    "ibge": m[0], "uf": m[2], "cidade": m[1], "url": "", "sistema": "",
                    "situacao": "desconhecido", "evidencia": f"erro: {erro.__class__.__name__}",
                }  # fmt: skip
            finally:
                feitos += 1
                if feitos % 25 == 0:
                    print(f"  {feitos} de {len(cidades)}", flush=True)

    try:
        return await asyncio.gather(*(uma(m) for m in cidades))
    finally:
        await d.fechar()


def gravar(resultados: list[dict], destino: Path = SAIDA) -> None:
    with destino.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(resultados, key=lambda r: (r["uf"], r["cidade"])):
            w.writerow(r)


def principal() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--uf", nargs="*")
    p.add_argument("--limite", type=int)
    p.add_argument("--conexoes", type=int, default=12)
    p.add_argument("--de-raw", action="store_true", help="reaproveita o que já foi sondado")
    p.add_argument(
        "--refazer", choices=["bloqueados", "sem-sistema"], help="com --de-raw, refaz esses"
    )
    a = p.parse_args()
    cidades = ler_cidades(a.uf)[: a.limite]
    t = time.time()
    resultados = asyncio.run(varrer(cidades, a.conexoes, a.de_raw, a.refazer))
    if not a.limite and not a.uf:
        gravar(resultados)
    achou = [r for r in resultados if r["url"]]
    print(f"{len(achou)} de {len(resultados)} com site; {time.time() - t:.0f} s")


if __name__ == "__main__":
    principal()
