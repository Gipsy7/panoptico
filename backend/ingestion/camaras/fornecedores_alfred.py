"""Câmaras com site próprio ou de fornecedor que ainda não tinham leitor: vereadores da
legislatura 2025–2028 com nome, nome civil, partido e foto. Um leitor por modelo de página, todos
na mesma carga (como `sistemas`), com a lista de câmaras aqui mesmo (`CAMARAS`).

- `camarasempapel` (Aracruz-ES, Cachoeiro de Itapemirim-ES): Câmara Sem Papel / NoPaperCloud
  (PLE, o mesmo produto). `parlamentares.aspx` mostra a legislatura atual (cabeçalho com as datas
  da legislatura) em blocos "Ativo", "Suplente" e "Licença"; só os "Ativo" entram. Cachoeiro
  escreve "Nome civil (Apelido)"; Aracruz, só o nome de urna em maiúsculas. Uma requisição.
- `webline` (Varjão de Minas-MG): a página "Vereadores" (`?pag=...`) lista "Nome civil - SIGLA"
  da legislatura em curso. Uma requisição.
- `nortelandia` (Nortelândia-MT): `/camara/vereadores` traz um cartão por vereador da gestão
  2025–2028 (nome civil, nome de urna quando houver, "SIGLA - Nome do partido"). Uma requisição.
- `cambuca` (Santa Maria do Cambuca-PE): o portal da transparência monta a tabela por JavaScript,
  a partir de `vereadoresClass.php?legislatura=<id>` (JSON público que a própria página chama).
  Duas requisições (a página, para achar a legislatura 2025–2028, e o JSON). O JSON não traz
  partido (campo vazio) e traz data de nascimento, telefone e e-mail: nada disso é lido.
- `alvorada` (Alvorada-TO): `/transparencia/vereador` (Composição da Casa Legislativa) tem um
  cartão por vereador com nome (e apelido entre parênteses, às vezes o cargo da mesa depois de
  " - ") e partido. Data de nascimento, ocupação etc. do cartão não são lidos. Uma requisição.

Fora: projetos, votos e presença. Respeita o `robots.txt` (pedido proibido não é feito), uma
requisição por vez, com pausa e User-Agent identificado. Grava nas mesmas tabelas do SAPL, pela
gravação dele (inclusive a ligação ao eleito do TSE).
"""

import argparse
import html
import json
import re
import time
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "fornecedores_alfred_camaras"
ACEITA = "text/html,application/xhtml+xml,application/json"
LEGISLATURA = ("2025-01-01", "2028-12-31")
PAUSA = 3.0

# (ibge, cidade, modelo de página, endereço da lista de vereadores)
CAMARAS = (
    ("3200607", "Aracruz", "camarasempapel", "https://aracruz.camarasempapel.com.br/parlamentares.aspx"),
    ("3201209", "Cachoeiro de Itapemirim", "camarasempapel", "https://cachoeiro.nopapercloud.com.br/parlamentares.aspx"),
    ("3170750", "Varjão de Minas", "webline", "https://varjaodeminas.mg.leg.br/?pag=T1RjPU9EZz1PVFU9T0dFPU9EWT1PR0k9T1RZPU9XST1PR1U9T1dVPQ=="),
    ("5106000", "Nortelândia", "nortelandia", "https://nortelandia.mt.leg.br/camara/vereadores"),
    ("2612703", "Santa Maria do Cambucá", "cambuca", "https://transparencia.santamariadocambuca.pe.leg.br/vereadores.php"),
    ("1700707", "Alvorada", "alvorada", "https://alvorada.to.leg.br/transparencia/vereador"),
    # Câmara Sem Papel: cinco câmaras do ES achadas pela descoberta de sistemas (27/10/2026).
    ("3200409", "Anchieta", "camarasempapel", "https://anchieta.camarasempapel.com.br/parlamentares.aspx"),
    ("3201001", "Boa Esperança", "camarasempapel", "https://boaesperanca.camarasempapel.com.br/parlamentares.aspx"),
    ("3201308", "Cariacica", "camarasempapel", "https://cariacica.camarasempapel.com.br/parlamentares.aspx"),
    ("3203205", "Linhares", "camarasempapel", "https://linhares.camarasempapel.com.br/parlamentares.aspx"),
    ("3203320", "Marataízes", "camarasempapel", "https://marataizes.camarasempapel.com.br/parlamentares.aspx"),
)  # fmt: skip

# Partidos que os sites escrevem por extenso ou com o nome da federação.
PARTIDOS = {"UNIÃO BRASIL": "UNIÃO", "UNIAO BRASIL": "UNIÃO"}


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def _decodificar(conteudo: bytes) -> str:
    """Alguns sites declaram UTF-8 e mandam Latin-1 (Câmara Sem Papel, Nortelândia, Alvorada)."""
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", "replace")


def _partido(texto: str | None) -> str | None:
    texto = _texto(texto or "")
    return PARTIDOS.get(texto.upper(), texto)[:30] or None


def _nomes(texto: str) -> tuple[str, str | None]:
    """'Nome civil (Apelido)' -> (apelido, nome civil); sem parênteses, (nome, None)."""
    texto = _texto(texto)
    achado = re.fullmatch(r"(.*?)\s*\((.+)\)", texto)
    if achado and achado[1]:
        return comum.nome_proprio(achado[2]) or achado[2], comum.nome_proprio(achado[1])
    return comum.nome_proprio(texto) or texto, None


def _vereador(id_externo: str, nome: str, completo: str | None, partido: str | None,
              foto: str | None = None) -> dict:  # fmt: skip
    return {
        "id_externo": sapl.id_curto(id_externo),
        "nome": nome,
        "nome_completo": completo if completo and completo != nome else None,
        "partido": partido,
        "foto_url": foto,
        "email": None,
        "telefone": None,
        "titular": True,
        "em_exercicio": True,
        "inicio": LEGISLATURA[0],
        "fim": LEGISLATURA[1],
        "proposicoes_por_tipo": {},
        "projetos": [],
    }


# --- Câmara Sem Papel / NoPaperCloud ------------------------------------------------------

SELO = re.compile(r"legend-pill legend-elevate'>\s*(.*?)\s*</div>", re.S)
DATAS_CSP = re.compile(r'legislatura_data"[^>]*>\s*(.*?)\s*</h5>', re.S)
CARTAO_CSP = re.compile(
    r"kt-widget__img' src='([^']*)'.*?"
    r"href='parlamentar\.aspx\?id=(\d+)' class='kt-widget__username pb-1'>\s*(.*?)\s*</a>"
    r".*?<small>\((.*?)\)</small>",
    re.S,
)


def vereadores_camarasempapel(pagina: str, base: str) -> list[dict]:
    """Os 'Ativo' da legislatura que começa em 2025 (outra legislatura na página: nada)."""
    datas = DATAS_CSP.search(pagina)
    if not datas or "/2025 a " not in _texto(datas[1]):
        return []
    marcas = [(m.start(), _texto(m[1]).lower()) for m in SELO.finditer(pagina)]
    achados = []
    for i, (inicio, rotulo) in enumerate(marcas):
        if not rotulo.startswith("ativo"):
            continue
        fim = marcas[i + 1][0] if i + 1 < len(marcas) else len(pagina)
        for foto, id_, nome, partido in CARTAO_CSP.findall(pagina[inicio:fim]):
            apelido, civil = _nomes(nome)
            achados.append(_vereador(id_, apelido, civil, _partido(partido), urljoin(base, foto)))
    return achados


# --- Weblinesistemas (Varjão de Minas) ----------------------------------------------------

ITEM_WEBLINE = re.compile(r'<a href="[^"]*idver=(\d+)[^"]*"\s*>(.*?)</a>', re.S)


def vereadores_webline(pagina: str, base: str) -> list[dict]:
    if "2025" not in _texto(re.sub(r"(?s)<tbody.*", "", pagina[pagina.find("tituloPagina") :])):
        return []
    achados = []
    for id_, texto in ITEM_WEBLINE.findall(pagina):
        nome, _, partido = _texto(texto).rpartition(" - ")
        if nome:
            achados.append(
                _vereador(id_, comum.nome_proprio(nome) or nome, None, _partido(partido))
            )
    return achados


# --- Nortelândia --------------------------------------------------------------------------

CARTAO_NORTELANDIA = re.compile(
    r'<img src="([^"]*)"[^>]*foto-circulo[^>]*>.*?<h3 class="nome-civil">(.*?)</h3>\s*'
    r'<p class="nome-urna">(.*?)</p>.*?<span class="badge-partido">(.*?)</span>.*?'
    r'href="/vereador/[^"]*/(\d+)"',
    re.S,
)


def vereadores_nortelandia(pagina: str, base: str) -> list[dict]:
    if not re.search(r"gest.o 2025 - 2028", pagina):
        return []
    achados = []
    raiz = "{0.scheme}://{0.netloc}/".format(urlparse(base))
    for foto, civil, urna, partido, id_ in CARTAO_NORTELANDIA.findall(pagina):
        civil, urna = _texto(civil), _texto(urna)
        sigla = _texto(partido).split(" - ")[0]
        # a página tem <base href="/">: a foto é relativa à raiz do site, não a /camara/
        achados.append(_vereador(id_, urna or civil, civil, _partido(sigla), urljoin(raiz, foto)))
    return achados


# --- Santa Maria do Cambucá ---------------------------------------------------------------

LEGISLATURA_CAMBUCA = re.compile(r"<option value='(\d+)'[^>]*>\s*2025 - 2028\s*</option>")


def legislatura_cambuca(pagina: str) -> str | None:
    achado = LEGISLATURA_CAMBUCA.search(pagina)
    return achado[1] if achado else None


def vereadores_cambuca(corpo: str, base: str) -> list[dict]:
    """O JSON da tabela: só nome, nome de urna, foto e a situação (ativo e titular)."""
    dados = json.loads(corpo)
    achados = []
    for linha in dados["rows"]:
        if linha.get("ativo") != "S" or linha.get("titular") != "S":
            continue
        nome = " ".join((linha.get("nome_parlamentar") or linha["nome"]).split())
        foto = linha.get("arquivo")
        achados.append(
            _vereador(
                str(linha["id"]),
                nome,
                " ".join(linha["nome"].split()),
                _partido(linha.get("partido")),
                urljoin(base, f"sistema/uploads/parlamentares/{foto}") if foto else None,
            )
        )
    return achados


# --- Alvorada -----------------------------------------------------------------------------

CARTAO_ALVORADA = re.compile(
    r'<img src="([^"]*agente_politico/([0-9a-f-]+)\.[a-z]+)"[^>]*>.*?'
    r'<h5 class="card-title">(.*?)</h5>\s*<h5 class="card-title">(.*?)</h5>',
    re.S,
)


def vereadores_alvorada(pagina: str, base: str) -> list[dict]:
    achados = []
    for foto, id_, nome, partido in CARTAO_ALVORADA.findall(pagina):
        nome = re.sub(
            r"\s+-\s+[^()]*$", "", _texto(nome)
        )  # tira o cargo da mesa: " - 1º Secretário"
        apelido, civil = _nomes(nome)
        achados.append(_vereador(id_, apelido, civil, _partido(partido), foto))
    return achados


# --- Coleta -------------------------------------------------------------------------------


def _robots(client: httpx.Client, url: str) -> RobotFileParser:
    partes = urlparse(url)
    regras = RobotFileParser()
    try:
        resposta = client.get(f"{partes.scheme}://{partes.netloc}/robots.txt")
        regras.parse(
            resposta.text.splitlines() if resposta.status_code == 200 else ["User-agent: *"]
        )
    except httpx.HTTPError:
        regras.parse(["User-agent: *"])
    return regras


def coletar(url: str, modelo: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA
        regras = _robots(client, url)

        def pagina(endereco: str) -> str:
            if not regras.can_fetch(comum.USER_AGENT, endereco):
                raise PermissionError(f"robots.txt veda {endereco}")
            time.sleep(PAUSA)
            return _decodificar(comum.get_bytes(client, endereco))

        texto = pagina(url)
        if modelo == "camarasempapel":
            achados = vereadores_camarasempapel(texto, url)
        elif modelo == "webline":
            achados = vereadores_webline(texto, url)
        elif modelo == "nortelandia":
            achados = vereadores_nortelandia(texto, url)
        elif modelo == "alvorada":
            achados = vereadores_alvorada(texto, url)
        elif modelo == "cambuca":
            legislatura = legislatura_cambuca(texto)
            achados = []
            if legislatura:
                lista = urljoin(
                    url, f"vereadoresClass.php?legislatura={legislatura}&current=1&rowCount=100"
                )
                achados = vereadores_cambuca(pagina(lista), url)
        else:
            raise ValueError(f"modelo desconhecido: {modelo}")
    return {"base": url, "legislatura": None, "vereadores": achados}


def executar(limite: int | None = None) -> int:
    camaras = CAMARAS[:limite] if limite else CAMARAS
    total, falhas = 0, 0
    for ibge, cidade, modelo, url in camaras:
        try:
            camara = coletar(url, modelo)
            if not camara["vereadores"]:
                raise ValueError("nenhum vereador encontrado")
            with SessionLocal() as session:
                total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {cidade}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="sites das câmaras de Aracruz, Cachoeiro de Itapemirim, Varjão de Minas, "
                "Nortelândia, Santa Maria do Cambucá, Alvorada, Anchieta, Boa Esperança, "
                "Cariacica, Linhares e Marataízes",
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
