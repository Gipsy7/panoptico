"""Câmaras que saíram do SAPL para sites de fornecedores com poucas câmaras cada: um leitor
pequeno por modelo de página, todos na mesma carga (como `aos`, mas por sistema do catálogo).

- `nexlegis` (Palmas, TO): tema WordPress "araguaia". A capa traz um cartão por vereador (com
  o rótulo SUPLENTE em quem não é titular) e a ficha tem o nome civil e o partido. O
  `robots.txt` pede 5 s entre requisições (Crawl-Delay). Uma ficha por vereador.
- `digitaliza` (Teófilo Otoni, MG): `/vereadores` lista só quem está no cargo, com o nome civil
  (e o apelido entre parênteses) e o partido por extenso. Uma requisição.
- `siscam` (Frutal, MG): `/Vereadores` do portal `<cidade>.siscam.com.br` lista a legislatura
  atual (as anteriores ficam noutro link) com o nome civil e a sigla, cortada em 10 letras.
  Uma requisição.

Fora: projetos, votos e presença. Grava nas mesmas tabelas do SAPL, pela gravação dele
(inclusive a ligação ao eleito do TSE).
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

FONTE = "sistemas_camaras"
SISTEMAS = ("nexlegis", "digitaliza", "siscam")
ACEITA = "text/html,application/xhtml+xml"
LEGISLATURA = ("2025-01-01", "2028-12-31")
PAUSA = 5.0

# Partidos que os sites escrevem por extenso ou cortados (o resto já vem como sigla).
PARTIDOS = {
    "PARTIDO LIBERAL": "PL",
    "PARTIDO DEMOCRÁTICO TRABALHISTA": "PDT",
    "MOVIMENTO DEMOCRÁTICO BRASILEIRO": "MDB",
    "PARTIDO DA MOBILIZAÇÃO NACIONAL": "MOBILIZA",
    "PROGRESSISTAS": "PP",
    "PARTIDO NOVO": "NOVO",
    "UNIÃO BRASIL": "UNIÃO",
    "PARTIDO DOS TRABALHADORES": "PT",
    "PARTIDO SOCIAL DEMOCRÁTICO": "PSD",
    "PARTIDO SOCIALISTA BRASILEIRO": "PSB",
    "PARTIDO DA SOCIAL DEMOCRACIA BRASILEIRA": "PSDB",
    "PARTIDO COMUNISTA DO BRASIL": "PCdoB",
    "PARTIDO RENOVADOR TRABALHISTA BRASILEIRO": "PRTB",
    "PARTIDO RENOVAÇÃO DEMOCRÁTICA": "PRD",
    "REDE SUSTENTABILIDADE": "REDE",
    "SOLIDARIED": "SOLIDARIEDADE",
    "REPUBLICAN": "REPUBLICANOS",
}


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def _partido(texto: str) -> str | None:
    texto = _texto(texto)
    if "FE BRASIL" in texto.upper():  # "Federação BRASIL DA ESPERANÇA – FE BRASIL(PT/PC do B/PV)"
        return "FE BRASIL"
    return PARTIDOS.get(texto.upper(), texto)[:30] or None


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


# --- Digitaliza ---------------------------------------------------------------------------

ITEM_DIGITALIZA = re.compile(
    r'href="[^"]*/vereadores/(\d+)/detalhes".*?<img[^>]*src="([^"]*)".*?'
    r"<h6>(.*?)</h6>\s*<p>(.*?)</p>",
    re.S,
)


def vereadores_digitaliza(pagina: str, base: str) -> list[dict]:
    achados = []
    for id_, foto, nome, partido in ITEM_DIGITALIZA.findall(pagina):
        civil = _texto(nome)
        apelido = re.fullmatch(r"(.*?)\s*\((.+)\)", civil)
        completo, apelido = (apelido[1], apelido[2]) if apelido else (None, civil)
        achados.append(_vereador(id_, apelido, completo, _partido(partido), urljoin(base, foto)))
    return achados


# --- Siscam -------------------------------------------------------------------------------

ITEM_SISCAM = re.compile(
    r'<h4><a href="/Vereadores/Vereador/(\d+)">(.*?)</a></h4>\s*<p>\s*'
    r"<strong>Partido:</strong>(.*?)</p>",
    re.S,
)


def vereadores_siscam(pagina: str, base: str) -> list[dict]:
    return [
        _vereador(id_, _texto(nome), None, _partido(partido))
        for id_, nome, partido in ITEM_SISCAM.findall(pagina)
    ]


# --- Nexlegis (Palmas) --------------------------------------------------------------------

CARTAO_NEXLEGIS = re.compile(
    r'<a class="card-vereador[^"]*"\s+href="([^"]*/vereador/([^/"]+)/)"(.*?)</a>', re.S
)
CAMPO_NEXLEGIS = re.compile(
    r"<p[^>]*>\s*([^<]+?)\s*</p>\s*<div[^>]*wp-block-nwe-acf[^>]*>(.*?)</div>", re.S
)


def cartoes_nexlegis(capa: str) -> list[tuple[str, str, str, str | None]]:
    """(link da ficha, slug, apelido, foto) dos titulares da capa (sem o SUPLENTE)."""
    achados = []
    for link, slug, corpo in CARTAO_NEXLEGIS.findall(capa):
        if "SUPLENTE" in corpo.upper():
            continue
        apelido = re.search(r"<p[^>]*>([^<]*)</p>", corpo)
        foto = re.search(r'data-src="([^"]+)"', corpo)
        achados.append(
            (link, slug, _texto(apelido[1]) if apelido else slug, foto[1] if foto else None)
        )
    return achados


def ficha_nexlegis(pagina: str, slug: str, apelido: str, foto: str | None) -> dict:
    campos = {_texto(k).lower(): _texto(v) for k, v in CAMPO_NEXLEGIS.findall(pagina)}
    return _vereador(
        slug, apelido, campos.get("nome civil"), _partido(campos.get("partido", "")), foto
    )


# --- Coleta -------------------------------------------------------------------------------


def _pagina(client, url: str) -> str:
    return comum.get_bytes(client, url).decode("utf-8", "replace")


def coletar(url: str, sistema: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    raiz = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA
        if sistema == "digitaliza":
            base = raiz + "/vereadores"
            achados = vereadores_digitaliza(_pagina(client, base), base)
        elif sistema == "siscam":
            base = raiz + "/Vereadores"
            achados = vereadores_siscam(_pagina(client, base), base)
        else:
            base = raiz + "/"
            achados = []
            for link, slug, apelido, foto in cartoes_nexlegis(_pagina(client, base)):
                time.sleep(PAUSA)
                achados.append(ficha_nexlegis(_pagina(client, link), slug, apelido, foto))
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
            if not camara["vereadores"]:
                raise ValueError("nenhum vereador encontrado")
            with SessionLocal() as session:
                total += sapl.gravar(session, ibge, camara)
                session.commit()
        except Exception as erro:  # uma câmara fora do ar não derruba as outras
            print(f"  {url}: {erro.__class__.__name__}: {str(erro)[:120]}", flush=True)
            falhas += 1
        time.sleep(PAUSA)
    with SessionLocal() as session:
        session.add(
            FonteIngestao(
                fonte=FONTE,
                url=(
                    "sites das câmaras do catálogo data/canais_curados.csv "
                    "(Nexlegis, Digitaliza, Siscam)"
                ),
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
