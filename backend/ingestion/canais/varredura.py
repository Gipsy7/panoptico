"""Varredura inicial dos canais oficiais de cada município (prefeitura, câmara e portais de
transparência), feita uma vez. O resultado vira o catálogo versionado
`data/canais_oficiais.csv`, e as cargas seguintes vão direto aos endereços dele.

Como funciona, para cada cidade:
1. Testa os endereços padrão da prefeitura (`{cidade}.{uf}.gov.br`) e da câmara
   (`{cidade}.{uf}.leg.br`, `camara{cidade}.{uf}.gov.br`, `cm{cidade}...`).
2. Lê a página inicial da prefeitura (e da câmara, se achada) e aproveita os links para a
   câmara e para o portal da transparência.
3. Confere se a página é mesmo daquela cidade (o nome aparece no título ou no texto).
4. Se nenhum link "transparência" apareceu (menus montados por JavaScript não aparecem no
   HTML), sonda os endereços mais comuns: `/transparencia`, `/portal-da-transparencia` e o
   subdomínio `transparencia.{prefeitura}`. Só aceita página com "transparência" no título,
   porque muitos sites devolvem a página inicial (status 200) para qualquer endereço.
5. Reconhece o sistema usado: SAPL do Interlegis (pela API) e os fornecedores de portal de
   transparência mais comuns (pelo endereço do link).

Educação com os servidores: poucas conexões ao mesmo tempo, uma por site, identificação
do Panóptico no User-Agent e só domínios oficiais (.gov.br e .leg.br) como ponto de
partida. Um site oficial pode redirecionar para outro domínio .br; aceitamos o destino.
"""

import argparse
import asyncio
import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.models import Municipio
from ingestion.comum import USER_AGENT, chave_nome

CATALOGO = BACKEND_DIR.parent / "data" / "canais_oficiais.csv"
COLUNAS = ["ibge", "municipio", "uf", "tipo", "url", "sistema", "verificado_em"]

# Fornecedores de portal de transparência, reconhecidos pelo endereço do portal.
SISTEMAS = [
    ("betha", re.compile(r"betha\.cloud|bethacloud|betha\.com\.br", re.I)),
    ("ipm", re.compile(r"atende\.net|ipm\.com\.br|ipmsistemas", re.I)),
    ("fiorilli", re.compile(r"fiorilli|sctransparencia|scpi", re.I)),
    ("elotech", re.compile(r"elotech|oxy\.elotech", re.I)),
    ("govbr", re.compile(r"govbr\.com\.br|portaltransparencia\.govbr", re.I)),
    ("e-gov (sintese)", re.compile(r"e-gov\.betha|sintese|tdm\.com\.br", re.I)),
    ("aspec", re.compile(r"aspec\.com\.br", re.I)),
    ("portalfacil", re.compile(r"portalfacil", re.I)),
    ("cr2", re.compile(r"cr2\.co|cr2transparencia", re.I)),
    ("instar", re.compile(r"instar\.com\.br|transparencia\.app", re.I)),
    ("pronim (govbr)", re.compile(r"pronim|cidade360", re.I)),
    ("cittaweb", re.compile(r"cittaweb", re.I)),
    ("multi24", re.compile(r"multi24", re.I)),
    ("abase", re.compile(r"abase\.com\.br", re.I)),
    ("digifred", re.compile(r"digifred", re.I)),
    ("epublica", re.compile(r"epublica", re.I)),
]
# Links com "transparência" que não são o portal (campanhas, radares externos, covid).
NAO_E_PORTAL = re.compile(
    r"covid|vacina|radardatransparencia|atricon|ouvidoria|lgpd|/noticia|audiencia", re.I
)
OFICIAL = (".gov.br", ".leg.br")


def slugs(nome: str) -> list[str]:
    """Formas do nome usadas em domínios: 'São Bento do Sul' -> 'saobentodosul',
    'sao-bento-do-sul', 'saobentodsul' não (abreviações não são adivinháveis)."""
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9 ]", " ", base.replace("'", "")).split()
    juntos = "".join(base)
    com_hifen = "-".join(base)
    return list(dict.fromkeys([juntos, com_hifen]))


def candidatos(nome: str, uf: str) -> dict[str, list[str]]:
    uf = uf.lower()
    prefeitura, camara = [], []
    for s in slugs(nome):
        prefeitura += [f"https://{s}.{uf}.gov.br/", f"https://www.{s}.{uf}.gov.br/"]
        camara += [
            f"https://{s}.{uf}.leg.br/",
            f"https://www.{s}.{uf}.leg.br/",
            f"https://camara{s}.{uf}.gov.br/",
            f"https://www.camara{s}.{uf}.gov.br/",
            f"https://cm{s}.{uf}.gov.br/",
            f"https://www.cm{s}.{uf}.gov.br/",
        ]
    return {"prefeitura": prefeitura, "camara": camara}


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.titulo = ""
        self._no_titulo = False
        self._href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._no_titulo = True
        if tag == "a":
            self._href = dict(attrs).get("href")
            if self._href:
                self.links.append((self._href, ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self._no_titulo = False
        if tag == "a":
            self._href = None

    def handle_data(self, data):
        if self._no_titulo:
            self.titulo += data
        elif self._href and self.links:
            href, texto = self.links[-1]
            self.links[-1] = (href, texto + data)


@dataclass
class Pagina:
    url: str
    titulo: str
    texto: str
    links: list[tuple[str, str]] = field(default_factory=list)


def _juntar(base: str, href: str) -> str | None:
    """urljoin que não quebra com links malformados (ex.: "http://[facebook_entidade]")."""
    try:
        return urljoin(base, href)
    except ValueError:
        return None


def _da_cidade(pagina: Pagina, nome: str) -> bool:
    chave = chave_nome(nome)
    return chave in chave_nome(pagina.titulo) or chave in chave_nome(pagina.texto[:20000])


def _oficial(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host.endswith(OFICIAL)


def de_outra_cidade(url: str, nome: str) -> bool:
    """Link para o domínio oficial de OUTRA cidade (visto: modelo de site de fornecedor
    apontando para o portal de outro cliente). Domínios de fornecedores não entram aqui."""
    host = urlparse(url).hostname or ""
    if not host.endswith(OFICIAL):
        return False
    return not any(s.replace("-", "") in host.replace("-", "") for s in slugs(nome))


def limpar_catalogo(linhas: list[dict]) -> list[dict]:
    """Tira do catálogo os portais de transparência que caem nas armadilhas conhecidas."""
    return [
        linha
        for linha in linhas
        if not linha["tipo"].startswith("transparencia")
        or not (
            de_outra_cidade(linha["url"], linha["municipio"]) or NAO_E_PORTAL.search(linha["url"])
        )
    ]


def melhor_portal(pagina: Pagina, nome: str = "") -> str | None:
    """O link mais provável para o portal da transparência: o texto diz "transparência",
    não é a própria página inicial nem uma campanha, e um fornecedor conhecido vale mais."""
    inicio = pagina.url.rstrip("/")
    melhores: list[tuple[int, str]] = []
    for href, texto in pagina.links:
        absoluto = _juntar(pagina.url, href)
        if not absoluto:
            continue
        alvo = f"{absoluto} {texto}".lower()
        if "transpar" not in alvo or not absoluto.startswith("http"):
            continue
        if absoluto.rstrip("/") == inicio or NAO_E_PORTAL.search(alvo):
            continue
        if nome and de_outra_cidade(absoluto, nome):
            continue
        pontos = 0
        if "portal da transpar" in alvo or "portal transpar" in alvo:
            pontos += 3
        if "transpar" in texto.lower():
            pontos += 2
        if sistema_de(absoluto):
            pontos += 2
        melhores.append((pontos, absoluto))
    return max(melhores, key=lambda x: x[0])[1] if melhores else None


def sistema_de(url: str) -> str | None:
    for nome, padrao in SISTEMAS:
        if padrao.search(url):
            return nome
    return None


class Varredura:
    def __init__(self, conexoes: int = 48, tempo: float = 12.0, pausa: float = 0.6) -> None:
        self.limite = asyncio.Semaphore(conexoes)
        # Muitas cidades dividem o mesmo servidor (o mesmo IP): uma requisição por vez por
        # servidor, com pausa, senão o servidor nos bloqueia (visto em SC: resposta 444).
        self.pausa = pausa
        self.por_servidor: dict[str, asyncio.Lock] = {}
        self.ips: dict[str, str] = {}
        self.cliente = httpx.AsyncClient(
            timeout=httpx.Timeout(tempo),
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"},
            follow_redirects=True,
            verify=False,  # muitos sites municipais têm certificado vencido ou incompleto
        )

    async def fechar(self) -> None:
        await self.cliente.aclose()

    async def _servidor(self, url: str) -> asyncio.Lock | None:
        host = urlparse(url).hostname or ""
        if host not in self.ips:
            try:
                info = await asyncio.get_running_loop().getaddrinfo(host, 443)
                self.ips[host] = info[0][4][0]
            except OSError:
                self.ips[host] = ""  # domínio não existe: nem tenta conectar
        ip = self.ips[host]
        if not ip:
            return None
        return self.por_servidor.setdefault(ip, asyncio.Lock())

    async def _get(self, url: str) -> httpx.Response | None:
        trava = await self._servidor(url)
        if trava is None:
            return None
        async with trava, self.limite:
            try:
                return await self.cliente.get(url)
            except (httpx.HTTPError, UnicodeDecodeError, ValueError):
                return None
            finally:
                await asyncio.sleep(self.pausa)

    async def pagina(self, url: str) -> Pagina | None:
        resposta = await self._get(url)
        if resposta is None:
            return None
        tipo = resposta.headers.get("content-type", "")
        if resposta.status_code != 200 or "html" not in tipo:
            return None
        html = resposta.text[:400_000]
        leitor = _Links()
        try:
            leitor.feed(html)
        except Exception:  # HTML quebrado: segue com o que deu para ler
            pass
        texto = re.sub(r"<[^>]+>", " ", html)
        return Pagina(str(resposta.url), leitor.titulo.strip(), texto, leitor.links)

    async def achar_sapl(self, url_camara: str) -> str | None:
        host = (urlparse(url_camara).hostname or "").removeprefix("www.")
        for base in (f"https://sapl.{host}/", url_camara):
            if await self.e_sapl(base):
                return base
        return None

    async def e_sapl(self, url: str) -> bool:
        resposta = await self._get(urljoin(url, "/api/parlamentares/parlamentar/?page_size=1"))
        return (
            resposta is not None
            and resposta.status_code == 200
            and "results" in resposta.text[:2000]
        )

    async def sondar_portal(self, url_site: str) -> str | None:
        """Portal da transparência nos endereços mais comuns, quando a página inicial não
        tem o link no HTML."""
        host = (urlparse(url_site).hostname or "").removeprefix("www.")
        base = f"{urlparse(url_site).scheme}://{urlparse(url_site).hostname}"
        for url in (
            f"https://transparencia.{host}/",
            f"{base}/portal-da-transparencia",
            f"{base}/transparencia",
            f"{base}/portaltransparencia",
        ):
            pagina = await self.pagina(url)
            if pagina and "transpar" in chave_nome(pagina.titulo).lower():
                return pagina.url
        return None

    async def primeira(self, urls: list[str], nome: str) -> Pagina | None:
        for url in urls:
            pagina = await self.pagina(url)
            if pagina and _da_cidade(pagina, nome):
                return pagina
        return None

    async def cidade(self, ibge: str, nome: str, uf: str) -> list[dict]:
        hoje = date.today().isoformat()
        achados: list[dict] = []

        def anotar(tipo: str, url: str, sistema: str | None = None) -> None:
            if not any(a["tipo"] == tipo for a in achados):
                achados.append(
                    {
                        "ibge": ibge,
                        "municipio": nome,
                        "uf": uf,
                        "tipo": tipo,
                        "url": url,
                        "sistema": sistema or "",
                        "verificado_em": hoje,
                    }  # fmt: skip
                )

        tentativas = candidatos(nome, uf)
        prefeitura = await self.primeira(tentativas["prefeitura"], nome)
        if prefeitura:
            anotar("prefeitura", prefeitura.url)

        # Câmara: primeiro o link no site da prefeitura, depois os endereços padrão.
        links_camara = []
        if prefeitura:
            for href, texto in prefeitura.links:
                absoluto = _juntar(prefeitura.url, href)
                if not absoluto:
                    continue
                alvo = (absoluto + " " + texto).lower()
                if _oficial(absoluto) and (".leg.br" in absoluto or "camara" in alvo):
                    if urlparse(absoluto).hostname != urlparse(prefeitura.url).hostname:
                        links_camara.append(
                            f"{urlparse(absoluto).scheme}://{urlparse(absoluto).hostname}/"
                        )
        camara = await self.primeira(list(dict.fromkeys(links_camara + tentativas["camara"])), nome)
        if camara:
            anotar("camara", camara.url)
            # O SAPL (sistema legislativo do Interlegis) fica num subdomínio próprio,
            # sapl.{câmara}, com API aberta: é por ele que vêm vereadores e projetos.
            if sapl := await self.achar_sapl(camara.url):
                anotar("sapl", sapl, "sapl")

        # Portais da transparência: o melhor link "transparência" dos sites oficiais.
        for origem, pagina in (("prefeitura", prefeitura), ("camara", camara)):
            if not pagina:
                continue
            portal = melhor_portal(pagina, nome) or await self.sondar_portal(pagina.url)
            if portal:
                anotar(f"transparencia_{origem}", portal, sistema_de(portal))
        return achados


async def varrer(municipios: list[tuple[str, str, str]], conexoes: int) -> list[dict]:
    varredura = Varredura(conexoes)
    feitos = 0

    async def uma(m: tuple[str, str, str]) -> list[dict]:
        nonlocal feitos
        try:
            resultado = await varredura.cidade(*m)
        except Exception as erro:  # uma cidade com site estranho não derruba a varredura
            print(f"  {m[1]}/{m[2]}: {erro.__class__.__name__}: {str(erro)[:100]}")
            resultado = []
        feitos += 1
        if feitos % 100 == 0:
            print(f"  {feitos} de {len(municipios)} cidades")
        return resultado

    try:
        resultados = await asyncio.gather(*(uma(m) for m in municipios))
    finally:
        await varredura.fechar()
    return [linha for lista in resultados for linha in lista]


async def completar_portais(linhas: list[dict], ufs: list[str] | None, conexoes: int) -> list[dict]:
    """Sem refazer a varredura: para as cidades do catálogo com site da prefeitura ou da
    câmara mas sem portal da transparência, sonda os endereços comuns."""
    tem = {(x["ibge"], x["tipo"]) for x in linhas}
    pendentes = [
        x
        for x in linhas
        if x["tipo"] in ("prefeitura", "camara")
        and (x["ibge"], f"transparencia_{x['tipo']}") not in tem
        and (not ufs or x["uf"] in ufs)
    ]
    print(f"Sondando {len(pendentes)} sites sem portal da transparência...")
    varredura = Varredura(conexoes)
    hoje = date.today().isoformat()

    async def um(site: dict) -> dict | None:
        try:
            portal = await varredura.sondar_portal(site["url"])
        except Exception:
            return None
        if not portal or de_outra_cidade(portal, site["municipio"]):
            return None
        return {**site, "tipo": f"transparencia_{site['tipo']}", "url": portal,
                "sistema": sistema_de(portal) or "", "verificado_em": hoje}  # fmt: skip

    try:
        novos = [x for x in await asyncio.gather(*(um(p) for p in pendentes)) if x]
    finally:
        await varredura.fechar()
    print(f"Achados: {len(novos)}")
    return linhas + novos


def gravar_catalogo(linhas: list[dict], destino: Path = CATALOGO) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = sorted(limpar_catalogo(linhas), key=lambda x: (x["uf"], x["municipio"], x["tipo"]))
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)


def resumo(linhas: list[dict], total: int) -> str:
    por_tipo: dict[str, set[str]] = {}
    sistemas: dict[str, int] = {}
    for linha in linhas:
        por_tipo.setdefault(linha["tipo"], set()).add(linha["ibge"])
        if linha["sistema"]:
            chave = f"{linha['tipo']}: {linha['sistema']}"
            sistemas[chave] = sistemas.get(chave, 0) + 1
    partes = [f"{tipo}: {len(ids)} de {total} cidades" for tipo, ids in sorted(por_tipo.items())]
    partes += [f"{k}: {v}" for k, v in sorted(sistemas.items(), key=lambda x: -x[1])]
    return "\n".join(partes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Varredura dos canais oficiais dos municípios")
    parser.add_argument("--uf", nargs="*", help="Só estes estados (padrão: todos)")
    parser.add_argument("--limite", type=int, help="Só as N primeiras cidades (teste)")
    parser.add_argument("--conexoes", type=int, default=24)
    parser.add_argument("--saida", type=Path, default=CATALOGO)
    parser.add_argument(
        "--completar",
        action="store_true",
        help="Não varre de novo: só sonda o portal da transparência de quem está sem",
    )
    args = parser.parse_args()

    if args.completar:
        with CATALOGO.open(encoding="utf-8") as arquivo:
            atuais = list(csv.DictReader(arquivo))
        ufs = [u.upper() for u in args.uf] if args.uf else None
        gravar_catalogo(asyncio.run(completar_portais(atuais, ufs, args.conexoes)), args.saida)
        raise SystemExit

    with SessionLocal() as session:
        consulta = select(Municipio.ibge, Municipio.nome, Municipio.uf).order_by(
            Municipio.uf, Municipio.nome
        )
        if args.uf:
            consulta = consulta.where(Municipio.uf.in_([u.upper() for u in args.uf]))
        municipios = [tuple(m) for m in session.execute(consulta).all()]
    if args.limite:
        municipios = municipios[: args.limite]
    print(f"Varrendo {len(municipios)} cidades...")
    linhas = asyncio.run(varrer(municipios, args.conexoes))
    gravar_catalogo(linhas, args.saida)
    print(resumo(linhas, len(municipios)))
    print(f"Catálogo: {args.saida}")
