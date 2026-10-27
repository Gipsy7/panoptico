"""Câmaras de fornecedores que cobrem muitas cidades pequenas de uma vez: vereadores em
exercício (nome, partido, foto quando estável), um leitor por sistema, todos na mesma carga.
As cidades vêm do catálogo (`data/canais_oficiais.csv`, tipo "sistema_legislativo", coluna
`sistema`), achadas por `ingestion.canais.descobrir_sistemas`.

- `webservicesistemas` (MA, 15 câmaras): o site é um Nuxt que monta a lista no navegador, a
  partir de `/api/vereadores` (JSON público, o mesmo que a página chama). Um registro por
  vereador: nome civil, `nome_eleicao` (nome de urna), partido (`sigla`) e `status`.
- `sts` (PI, 10 câmaras; STS Informática, portal `acessoainformacao`): a página
  `<câmara>/acessoinformacao/parlamentares` traz a legislatura mais recente numa tabela (nome
  civil, nome parlamentar e partido). Uma requisição.
- `cespro` (RS, ~14 câmaras; modelo `/site` da Cespro, o mesmo das câmaras com transparência
  Abase): `/site/vereadores` lista quem está no cargo (o menu "Vereadores"); o nome vem com a
  sigla entre parênteses em parte das câmaras, e a ficha (`Partido: ...`) completa o resto.
- `icamaras` (RS, 6 câmaras; Visão Informática): `/vereadores` tem um cartão por vereador, com o
  partido no título da imagem. Uma requisição.
- `portalfacil` (MG, 7 câmaras; Actcon / Portal Fácil): a capa leva à lista da legislatura
  (`/parlamentares/legislatura/<id>-2025-2028/3`), que traz um cartão por vereador com o
  partido na legenda da bandeira. Duas requisições.
- `ingadigital` (PR, 20 câmaras; Ingá Digital): a capa tem o link "VEREADORES" (com um código de
  sessão que muda), e a página lista os nomes por legislatura. Só o nome: o site não publica
  o partido (a ligação com o eleito do TSE completa). Duas requisições.

Fora: projetos, votos e presença (os portais não têm formato aberto). Dado pessoal fica de
fora: data de nascimento, telefone, e-mail e endereço dos cartões e fichas não são lidos.
Respeita o `robots.txt` (caminho vedado não é pedido; as câmaras com `User-agent: * Disallow: /`
nem entram no catálogo), uma requisição por vez e pausa entre elas. Grava nas mesmas tabelas
do SAPL, pela gravação dele (inclusive a ligação ao eleito do TSE).
"""

import argparse
import html
import json
import re
import time
import unicodedata
from datetime import UTC, date, datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Candidatura, FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl
from ingestion.canais import catalogo
from ingestion.identidade import casar_nome

FONTE = "fornecedores_cobertura_camaras"
SISTEMAS = ("webservicesistemas", "sts", "cespro", "icamaras", "portalfacil", "ingadigital")
ACEITA = "text/html,application/xhtml+xml,application/json"
LEGISLATURA = ("2025-01-01", "2028-12-31")
PAUSA = 2.0
TOLERADO = (3, 25)  # menos ou mais vereadores que isso é página errada, não câmara

# Partidos por extenso (sem acento, maiúsculas) -> sigla como o TSE escreve.
PARTIDOS = {
    "MOVIMENTO DEMOCRATICO BRASILEIRO": "MDB",
    "PARTIDO DOS TRABALHADORES": "PT",
    "PARTIDO DEMOCRATICO TRABALHISTA": "PDT",
    "PARTIDO SOCIALISTA BRASILEIRO": "PSB",
    "PARTIDO DA SOCIAL DEMOCRACIA BRASILEIRA": "PSDB",
    "PARTIDO SOCIAL DEMOCRATICO": "PSD",
    "PARTIDO LIBERAL": "PL",
    "PROGRESSISTAS": "PP",
    "PARTIDO PROGRESSISTA": "PP",
    "REPUBLICANOS": "REPUBLICANOS",
    "UNIAO BRASIL": "UNIÃO",
    "UNIAO": "UNIÃO",
    "PODEMOS": "PODE",
    "SOLIDARIEDADE": "SOLIDARIEDADE",
    "PARTIDO COMUNISTA DO BRASIL": "PCdoB",
    "PARTIDO VERDE": "PV",
    "PARTIDO NOVO": "NOVO",
    "NOVO": "NOVO",
    "PARTIDO DA MOBILIZACAO NACIONAL": "MOBILIZA",
    "MOBILIZA": "MOBILIZA",
    "AVANTE": "AVANTE",
    "AGIR": "AGIR",
    "CIDADANIA": "CIDADANIA",
    "REDE SUSTENTABILIDADE": "REDE",
    "PARTIDO RENOVACAO DEMOCRATICA": "PRD",
    "PARTIDO SOCIALISMO E LIBERDADE": "PSOL",
    "DEMOCRACIA CRISTA": "DC",
    "PARTIDO DA MULHER BRASILEIRA": "PMB",
    "PARTIDO RENOVADOR TRABALHISTA BRASILEIRO": "PRTB",
}


SIGLAS = set(PARTIDOS.values()) | {
    "PSTU", "PCB", "PCO", "UP", "PRTB", "PMN", "DEM", "PTB", "PROS", "PSC", "PATRI", "PHS",
    "PPS", "PRB", "PPL", "PEN", "SD", "PMDB", "PR", "PRP", "PTC", "PT DO B", "PC DO B",
}  # fmt: skip


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def partido(texto: str | None) -> str | None:
    """A sigla do partido, venha como vier: 'PARTIDO PP', 'Progressistas (PP)', 'União Brasil',
    'UNIAO', 'MDB'. Texto que não parece partido (data, outro campo) devolve None."""
    texto = _texto(texto or "")
    if not texto or re.search(r"\d{2}/\d{2}/\d{4}|nascimento", texto, re.I):
        return None
    entre_parenteses = re.search(r"\(([A-Za-zÀ-ú]{2,14})\)\s*$", texto)
    if entre_parenteses:
        texto = entre_parenteses[1]
    chave = _sem_acento(texto)
    if chave.startswith("PARTIDO ") and chave not in PARTIDOS:
        chave = chave.removeprefix("PARTIDO ")
    if chave in PARTIDOS:
        return PARTIDOS[chave]
    chave = {"PODEMOS": "PODE", "UNIAO": "UNIÃO", "PCDOB": "PCdoB"}.get(chave, chave)
    return chave if chave in SIGLAS else None


def _nome(texto: str) -> str:
    """Nome como o site mostra, sem o tratamento 'Vereador(a)', sem 'LICENCIADO' e sem a sigla
    entre parênteses; caixa alta vira nome próprio."""
    texto = _texto(texto)
    texto = re.sub(r"^(?:Ver\.|Vereador(?:a)?)\s+", "", texto, flags=re.I)
    texto = re.sub(r"\s*-\s*(?:LICENCIAD[OA]|AFASTAD[OA]|SUPLENTE).*$", "", texto, flags=re.I)
    texto = re.sub(r"\s*\([^)]{1,30}\)\s*$", "", texto)
    return comum.nome_proprio(texto.strip()) or texto.strip()


FORA_DA_LISTA = re.compile(r"comiss|bancada|mesa diretora|legislatura|presidente da|secret", re.I)


def nome_e_partido(texto: str) -> tuple[str, str | None]:
    """'Nome - PSB - PRESIDENTE', 'Nome-pt', 'Nome (PT)' -> (nome, sigla ou None)."""
    texto = _texto(texto)
    texto = re.sub(r"^(?:Ver\.|Vereador(?:a)?)\s+", "", texto, flags=re.I)
    texto = re.sub(r"\s*-\s*(?:LICENCIAD[OA]|AFASTAD[OA]|SUPLENTE).*$", "", texto, flags=re.I)
    entre = re.search(r"\(([A-Za-zÀ-ú/ ]{2,20})\)\s*$", texto)
    if entre and partido(entre[1]):
        return _proprio(texto[: entre.start()]), partido(entre[1])
    partes = [x.strip() for x in re.split(r"\s+-\s+|(?<=\w)-(?=[A-Za-z]{2,12}$)", texto)]
    if len(partes) > 1 and partido(partes[1]):
        return _proprio(partes[0]), partido(partes[1])
    if len(partes) > 1 and "/" in partes[1]:  # federação: "PSDB/CIDADANIA"
        siglas = [partido(x) for x in partes[1].split("/")]
        if all(siglas):
            return _proprio(partes[0]), siglas[0]
    return _proprio(texto), None


def _proprio(nome: str) -> str:
    nome = nome.strip()
    return comum.nome_proprio(nome) or nome


def _vereador(id_externo: str, nome: str, completo: str | None, sigla: str | None,
              foto: str | None = None) -> dict:  # fmt: skip
    return {
        "id_externo": sapl.id_curto(id_externo),
        "nome": nome,
        "nome_completo": completo if completo and completo != nome else None,
        "partido": sigla,
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


# --- webservicesistemas (MA) -----------------------------------------------------------------


def vereadores_webservices(corpo: str, base: str) -> list[dict]:
    """O JSON de `/api/vereadores`: só os publicados; o partido vem como objeto com `sigla`."""
    achados = []
    for v in json.loads(corpo):
        if v.get("status") != "published" or not v.get("nome"):
            continue
        sigla = partido(
            (v.get("partido") or {}).get("sigla") or (v.get("partido") or {}).get("nome")
        )
        civil = comum.nome_proprio(_texto(v["nome"]))
        urna = comum.nome_proprio(_texto(v.get("nome_eleicao") or "")) or civil
        foto = v.get("foto")
        achados.append(
            _vereador(
                str(v.get("id") or v.get("slug")),
                urna,
                civil,
                sigla,
                f"https://nexus.webservicesistemas.com.br/assets/{foto}" if foto else None,
            )
        )
    return achados


# --- sts (PI) -------------------------------------------------------------------------------

LINHA_STS = re.compile(
    r'<tr>\s*<td[^>]*>.*?</td>\s*<td[^>]*><a href="[^"]*parlamentar/?\?id=(\d+)">'
    r"<strong>(.*?)</strong></a></td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>",
    re.S,
)


def vereadores_sts(pagina: str, base: str) -> list[dict]:
    """A tabela da legislatura mais recente: nome civil, nome parlamentar e partido."""
    achados = []
    for id_, civil, urna, sigla in LINHA_STS.findall(pagina):
        civil, urna = _texto(civil), _texto(urna)
        achados.append(
            _vereador(
                id_,
                _nome(urna or civil),
                comum.nome_proprio(civil),
                partido(sigla),
            )
        )
    return achados


# --- cespro (RS) ----------------------------------------------------------------------------

LINK_CESPRO = re.compile(
    r'<a href="(?:\.\./)?(/?site/vereadores/(\d+)-[^"]*)"[^>]*>(.*?)</a>', re.S
)
FICHA_PARTIDO = re.compile(r"Partido\s*:?\s*(?:</[^>]+>\s*)*(?:<[^>]+>\s*)*([^<\n]{2,80})", re.I)
FICHA_NOME = re.compile(r"Nome\s*:\s*(?:</[^>]+>\s*)*(?:<[^>]+>\s*)*([^<\n]{3,80})", re.I)


def links_cespro(pagina: str) -> list[tuple[str, str, str]]:
    """(id, caminho da ficha, nome como aparece) de cada vereador da lista, sem repetir; fica
    o texto mais longo de cada id (o menu repete o nome com a sigla)."""
    por_id: dict[str, tuple[str, str]] = {}
    for caminho, id_, corpo in LINK_CESPRO.findall(pagina):
        texto = _texto(corpo)
        if texto.upper() in {"CLIQUE PARA MAIS INFORMAÇÕES", ""} and id_ in por_id:
            continue
        if id_ not in por_id or len(texto) > len(por_id[id_][1]):
            por_id[id_] = (caminho if caminho.startswith("/") else "/" + caminho, texto)
    return [(i, c, t) for i, (c, t) in por_id.items() if t and not FORA_DA_LISTA.search(t)]


def sigla_do_menu(texto: str) -> str | None:
    return nome_e_partido(texto)[1]


def ficha_cespro(pagina: str) -> tuple[str | None, str | None]:
    """(nome civil, partido) da ficha: 'Nome: ...' e 'Partido: ...' (ou a linha seguinte)."""
    nome = FICHA_NOME.search(pagina)
    sigla = None
    for achado in FICHA_PARTIDO.finditer(pagina):
        sigla = partido(achado[1].strip(": "))
        if sigla:
            break
    return (comum.nome_proprio(_texto(nome[1])) if nome else None), sigla


# --- icamaras (RS) --------------------------------------------------------------------------

BLOCO_ICAMARAS = re.compile(r"<!-- VEREADOR -->(.*?)<!-- /VEREADOR -->", re.S)
TITULO_ICAMARAS = re.compile(r'<a title="([^"]*)" href="[^"]*/vereador/(\d+)/')
FOTO_ICAMARAS = re.compile(r'class="img-responsive img-circle avatar" src="([^"]*)"')
PARTIDO_ICAMARAS = re.compile(r'<div class="partido[^>]*>.*?<img [^>]*title="([^"]*)"', re.S)


def vereadores_icamaras(pagina: str, base: str) -> list[dict]:
    """Um cartão por vereador (nome, foto, partido no título da imagem). A página mistura
    titulares e suplentes sem nenhum rótulo, então nenhum é marcado em exercício aqui:
    `confirmar_pelo_tse` marca só quem foi eleito vereador na própria cidade (TSE 2024)."""
    achados = []
    for bloco in BLOCO_ICAMARAS.findall(pagina):
        titulo, foto, sigla = (
            TITULO_ICAMARAS.search(bloco),
            FOTO_ICAMARAS.search(bloco),
            PARTIDO_ICAMARAS.search(bloco),
        )
        if not titulo:
            continue
        v = _vereador(
            titulo[2],
            comum.nome_proprio(_texto(titulo[1])),
            None,
            partido(sigla[1]) if sigla else None,
        )
        v["foto_url"] = foto[1] if foto else None
        v["titular"] = v["em_exercicio"] = False
        achados.append(v)
    return achados


def confirmar_pelo_tse(session: Session, ibge: str, vereadores: list[dict]) -> int:
    """Marca titular e em exercício só quem tem vínculo forte (nome único) com um eleito
    (ELEITO, ELEITO POR QP ou POR MÉDIA) para vereador da cidade na última eleição municipal
    já encerrada: a mesma regra de ligação da gravação do SAPL. Devolve quantos confirmou."""
    ultima = session.scalar(
        select(func.max(Candidatura.ano_eleicao)).where(
            Candidatura.municipio_ibge == ibge,
            Candidatura.cargo == "VEREADOR",
            Candidatura.ano_eleicao < date.today().year,
        )
    )
    eleitos = session.execute(
        select(Candidatura.id, Candidatura.nome_urna, Candidatura.nome).where(
            Candidatura.municipio_ibge == ibge,
            Candidatura.cargo == "VEREADOR",
            Candidatura.ano_eleicao == ultima,
            Candidatura.situacao_turno.like("ELEITO%"),
        )
    ).all()
    nomes = [(id_, nome) for id_, urna, civil in eleitos for nome in (urna, civil)]
    confirmados = 0
    for v in vereadores:
        if casar_nome([v["nome"], v["nome_completo"]], nomes) is not None:
            v["titular"] = v["em_exercicio"] = True
            confirmados += 1
    return confirmados


# --- portalfacil (MG) -----------------------------------------------------------------------

LINK_LEGISLATURA = re.compile(
    r'href="([^"]*/parlamentares/legislatura/[^"]+)"[^>]*>\s*Vereadores', re.I
)
LINK_PARLAMENTARES = re.compile(r'href="((?:https?://[^"/]+)?/parlamentares)"', re.I)
CARTAO_PORTALFACIL = re.compile(
    r"<div class='divparlamentar[^']*'>.*?data-fresco-caption = '([^']*)'.*?"
    r"proc_leg_par_vis\.aspx\?cd=(\d+)' title='([^']*)'",
    re.S,
)
CARTAO_PF_FOTO = re.compile(r"proc_leg_par_vis\.aspx\?cd=(\d+)><img[^>]*src='([^']*)'", re.S)


def links_portalfacil(capa: str, base: str) -> list[str]:
    """A lista da legislatura (se a capa leva a ela) ou, como alternativa, `/parlamentares`."""
    achados = [LINK_LEGISLATURA.search(capa), LINK_PARLAMENTARES.search(capa)]
    return list(dict.fromkeys(urljoin(base, html.unescape(a[1])) for a in achados if a))


def vereadores_portalfacil(pagina: str, base: str) -> list[dict]:
    """Cada vereador aparece em várias abas da página (ordem alfabética, partido, comissões...):
    o partido vem da aba 'Partido político', em que a legenda da bandeira não é vazia."""
    por_id: dict[str, dict] = {}
    for sigla, id_, nome in CARTAO_PORTALFACIL.findall(pagina):
        atual = por_id.setdefault(id_, {"nome": comum.nome_proprio(_texto(nome)), "partido": None})
        atual["partido"] = atual["partido"] or partido(sigla)
    return [_vereador(id_, d["nome"], None, d["partido"]) for id_, d in por_id.items()]


# --- ingadigital (PR) -----------------------------------------------------------------------

LINK_INGA = re.compile(r'href="([^"]*index\.php\?sessao=[^"]+)"[^>]*>\s*VEREADORES\s*</a>', re.I)
LEGISLATURA_INGA = re.compile(r"(\d{4})\s*-\s*(\d{4})")


def link_vereadores_inga(capa: str, base: str) -> str | None:
    achado = LINK_INGA.search(capa)
    return urljoin(base, html.unescape(achado[1])) if achado else None


def vereadores_inga(pagina: str, base: str) -> list[dict]:
    """Os nomes sob o título '2025 - 2028' (os blocos antigos vêm depois). Sem partido."""
    texto = html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>", "", pagina, flags=re.S))
    linhas = [_texto(x) for x in re.sub(r"<[^>]+>", "\n", texto).splitlines()]
    linhas = [x for x in linhas if x]
    achados = []
    dentro = False
    for linha in linhas:
        legislatura = re.fullmatch(r"(\d{4}) - (\d{4})", linha)
        if legislatura:
            if dentro:
                break
            dentro = legislatura[1] == "2025"
            continue
        if not dentro:
            continue
        if linha.upper().startswith(("(SUPLENTE", "PROJETOS", "TRANSPAR", "CONTATO")):
            continue
        achados.append(linha)
    pares = [nome_e_partido(x) for x in achados if "(" not in x and 3 <= len(x) <= 120]
    return [_vereador(f"inga-{i}", n, None, sg) for i, (n, sg) in enumerate(pares, start=1)]


# --- Coleta -------------------------------------------------------------------------------


def _decodificar(conteudo: bytes) -> str:
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", "replace")


def _dominio(url: str) -> str:
    """O site da câmara sem o www (e sem o subdomínio, quando for .gov.br/.leg.br/.com.br)."""
    partes = (urlparse(url).hostname or "").split(".")
    return ".".join(
        partes[-3:] if partes[-2:-1] in (["gov"], ["leg"], ["com"], ["org"]) else partes[-2:]
    )


def _robots(client: httpx.Client, url: str) -> RobotFileParser:
    partes = urlparse(url)
    regras = RobotFileParser()
    try:
        resposta = client.get(f"{partes.scheme}://{partes.netloc}/robots.txt")
        e_texto = "html" not in resposta.headers.get("content-type", "")
        regras.parse(
            resposta.text.splitlines()
            if resposta.status_code == 200 and e_texto
            else ["User-agent: *"]
        )
    except httpx.HTTPError:
        regras.parse(["User-agent: *"])
    return regras


def coletar(url: str, sistema: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    raiz = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA
        regras = _robots(client, url)

        def pagina(endereco: str) -> str:
            if not regras.can_fetch(comum.USER_AGENT, endereco):
                raise PermissionError(f"robots.txt veda {endereco}")
            time.sleep(PAUSA)
            resposta = comum._get(client, endereco, None, comum.TENTATIVAS_PADRAO)
            if _dominio(str(resposta.url)) != _dominio(url):
                raise ValueError(f"{endereco} levou para outro site: {resposta.url}")
            return _decodificar(resposta.content)

        if sistema == "webservicesistemas":
            base = raiz + "/api/vereadores"
            achados = vereadores_webservices(pagina(base), base)
        elif sistema == "sts":
            base = url
            achados = vereadores_sts(pagina(base), base)
        elif sistema == "cespro":
            base = raiz + "/vereadores"
            lista = pagina(base)
            achados = []
            for id_, caminho, texto in links_cespro(lista):
                sigla = sigla_do_menu(texto)
                civil = None
                if not sigla:
                    civil, sigla = ficha_cespro(pagina(urljoin(base, caminho)))
                v = _vereador(id_, nome_e_partido(texto)[0], civil, sigla)
                v["em_exercicio"] = not re.search(r"licenciad|afastad", texto, re.I)
                achados.append(v)
        elif sistema == "icamaras":
            base = raiz + "/vereadores"
            achados = vereadores_icamaras(pagina(base), base)
        elif sistema == "portalfacil":
            base, achados = "", []
            for base in links_portalfacil(pagina(raiz + "/"), raiz + "/"):
                achados = vereadores_portalfacil(pagina(base), base)
                if achados:
                    break
        elif sistema == "ingadigital":
            base = link_vereadores_inga(pagina(raiz + "/"), raiz + "/") or ""
            achados = vereadores_inga(pagina(base), base) if base else []
        else:
            raise ValueError(f"sistema desconhecido: {sistema}")
    if sistema == "icamaras":
        return {"base": base, "legislatura": None, "vereadores": achados}  # ver executar()
    exercicio = sum(1 for v in achados if v["em_exercicio"])
    if not TOLERADO[0] <= exercicio <= TOLERADO[1]:
        raise ValueError(f"{exercicio} vereadores: página inesperada")
    if sistema not in ("webservicesistemas", "sts") and (exercicio % 2 == 0 or exercicio < 9):
        # Página lida do HTML: as cadeiras são sempre ímpares (9, 11, 13...); número par ou menor
        # que 9 sugere ex-vereador, suplente ou item de menu na lista. Melhor não gravar.
        raise ValueError(f"{exercicio} vereadores em exercício: contagem suspeita para HTML")
    return {"base": base, "legislatura": None, "vereadores": achados}


def executar(limite: int | None = None) -> int:
    camaras = [
        (c["municipio_ibge"], c["url"], c["sistema"])
        for c in catalogo.ler()
        if c["tipo"] == "sistema_legislativo" and c["sistema"] in SISTEMAS
    ]
    camaras = camaras[:limite] if limite else camaras
    total, falhas = 0, 0
    for ibge, url, sistema in camaras:
        try:
            camara = coletar(url, sistema)
            with SessionLocal() as session:
                if sistema == "icamaras":
                    confirmados = confirmar_pelo_tse(session, ibge, camara["vereadores"])
                    if not TOLERADO[0] <= confirmados <= TOLERADO[1]:
                        raise ValueError(f"{confirmados} vereadores confirmados pelo TSE")
                total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {url}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url="sites das câmaras do catálogo data/canais_oficiais.csv (webservicesistemas, "
                "sts, cespro, icamaras, portalfacil, ingadigital)",
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
