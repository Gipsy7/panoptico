"""Câmaras que saíram do SAPL para sites de fornecedores e que ganharam leitor próprio: um
leitor pequeno por modelo de página, todos na mesma carga (como `sistemas.py`).

- `instar` (Pimenta Bueno, RO): a capa do site traz o bloco "Legislatura" (01/01/2025 -
  31/12/2028) e um cartão por vereador, com o nome civil (no `alt` da foto), o id da ficha, a
  foto e o partido; a capa abrevia o nome de urna, então ele vem do JSON de dados abertos do
  próprio site (`/portal/dados-abertos/vereadores/<ano>`, ligado pelo nome civil). A página
  `/portal/vereadores` carrega a lista por script, por isso se lê a capa. Duas requisições.
- `legislador` (Perdões, MG): a capa do site da câmara traz um cartão por vereador (nome e
  cargo); o partido só está no texto livre da biografia, então fica vazio. A foto vem com
  endereço assinado que vence em 20 minutos, então não é guardada. Uma requisição.
- `wordpress_vereador` (Santa Cruz, PE): tema WordPress com um tipo de conteúdo "vereador". A
  capa lista os vereadores no menu e a ficha tem o nome civil e "Partido: X" no texto. Uma
  ficha por vereador.

Fora: projetos, votos e presença. Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive
a ligação ao eleito do TSE). Câmaras lidas aqui tiveram o `robots.txt` conferido; as que vedam
robôs (São José da Varginha, MG), pedem login (Riozinho, RS) ou só têm lista antiga ou vazia
(Estiva, Ibotirama, Leópolis, Manoel Vitorino) não estão aqui: ver `data/pendencias_cobertura.csv`.
"""

import argparse
import html
import json
import re
import time
from datetime import UTC, date, datetime
from urllib.parse import urljoin

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "fornecedores_batgirl_camaras"
ACEITA = "text/html,application/xhtml+xml"
LEGISLATURA = ("2025-01-01", "2028-12-31")
PAUSA = 3.0

# (ibge, endereço do site, modelo de página)
CAMARAS = (
    ("1100189", "https://www.pimentabueno.ro.leg.br/", "instar"),
    ("3149903", "https://www.perdoes.mg.leg.br/", "legislador"),
    ("2612455", "http://santacruz.pe.leg.br/", "wordpress_vereador"),
)


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def _vereador(id_externo: str, nome: str, completo: str | None, partido: str | None,
              foto: str | None = None) -> dict:  # fmt: skip
    return {
        "id_externo": sapl.id_curto(id_externo),
        "nome": nome,
        "nome_completo": completo if completo and completo != nome else None,
        "partido": partido[:30] if partido else None,
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


# --- Instar (Pimenta Bueno) ---------------------------------------------------------------

LEGISLATURA_INSTAR = re.compile(r'p_area_legislatura.*?<span class="p_info">([^<]*)</span>', re.S)
CARTAO_INSTAR = re.compile(
    r'<div class="p_vereador[^"]*">\s*<a href="[^"]*/vereadores/(\d+)">.*?'
    r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)".*?'
    r'<div class="p_titulo p_nome_parlamentar">(.*?)</div>.*?'
    r'<div class="p_info p_partido">(.*?)</div>',
    re.S,
)


def vereadores_instar(capa: str, base: str, dados_abertos: str | None = None) -> list[dict]:
    """Os cartões da capa; recusa se a legislatura mostrada não for a de 2025-2028. O nome de
    urna vem do JSON de dados abertos (ligado pelo nome civil), quando houver."""
    legislatura = LEGISLATURA_INSTAR.search(capa)
    if not legislatura or "2025" not in legislatura[1] or "2028" not in legislatura[1]:
        raise ValueError("a capa não mostra a legislatura 2025-2028")
    urnas = {}
    if dados_abertos:
        urnas = {
            _texto(d["nome"]).lower(): _texto(d["nomeParlamentar"])
            for d in json.loads(dados_abertos).get("dados", [])
        }
    achados = []
    for id_, foto, civil, urna, partido in CARTAO_INSTAR.findall(capa):
        civil = _texto(civil)
        achados.append(
            _vereador(
                id_,
                urnas.get(civil.lower()) or _texto(urna),
                civil,
                re.sub(r"^Partido:\s*", "", _texto(partido)),
                urljoin(base, foto),
            )
        )
    return achados


# --- Legislador (Perdões) -----------------------------------------------------------------

CARTAO_LEGISLADOR = re.compile(
    r"<h3>([^<]*)</h3>\s*<a href=\"[^\"]*WCI=Vereador&(?:amp;)?ID=\d+&(?:amp;)?ver=(\d+)\"", re.S
)


def vereadores_legislador(capa: str, base: str) -> list[dict]:
    return [
        _vereador(f"ver{ver}", _texto(nome), None, None)
        for nome, ver in CARTAO_LEGISLADOR.findall(capa)
    ]


# --- WordPress com tipo "vereador" (Santa Cruz) -------------------------------------------

MENU_VEREADOR = re.compile(
    r'<li id="menu-item-\d+" class="menu-item[^"]*"><a href="(https?://[^"]*/vereador/([^/"]+)/)">'
    r"(.*?)</a>",
    re.S,
)
CORPO_WORDPRESS = re.compile(r'<div class="hentry[^"]*">(.*?)</div>\s*</div>', re.S)
PARTIDO_WORDPRESS = re.compile(r"Partido:\s*([^<\n]+)", re.I)
NOME_WORDPRESS = re.compile(
    r"<strong>([^<]+?)\s*(?:<br\s*/?>\s*)?</strong>\s*(?:<br\s*/?>\s*)?Partido:", re.I
)
FOTO_WORDPRESS = re.compile(r'<img[^>]*\bsrc="([^"]+)"')


def links_wordpress(capa: str) -> list[tuple[str, str, str]]:
    """(link da ficha, slug, nome do menu) de cada vereador do menu, sem repetir."""
    vistos = {}
    for link, slug, nome in MENU_VEREADOR.findall(capa):
        vistos.setdefault(slug, (link, slug, _texto(nome)))
    return list(vistos.values())


def ficha_wordpress(pagina: str, slug: str, nome: str) -> dict:
    corpo = CORPO_WORDPRESS.search(pagina)
    corpo = corpo[1] if corpo else pagina
    civil = NOME_WORDPRESS.search(corpo)
    partido = PARTIDO_WORDPRESS.search(corpo)
    foto = FOTO_WORDPRESS.search(corpo)
    completo = _texto(civil[1]) if civil else None
    return _vereador(
        slug,
        nome,
        completo if completo and len(completo) > len(nome) else None,
        _texto(partido[1]) if partido else None,
        foto[1] if foto else None,
    )


# --- Coleta -------------------------------------------------------------------------------


def coletar(url: str, modelo: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    raiz = url.rstrip("/") + "/"
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA

        def pagina(endereco: str) -> str:
            return comum.get_bytes(client, endereco).decode("utf-8", "replace")

        achados = []
        if modelo == "instar":
            capa = pagina(raiz)
            time.sleep(PAUSA)
            dados = pagina(f"{raiz}portal/dados-abertos/vereadores/{date.today().year}")
            achados = vereadores_instar(capa, raiz, dados)
        elif modelo == "legislador":
            achados = vereadores_legislador(pagina(raiz), raiz)
        elif modelo == "wordpress_vereador":
            for link, slug, nome in links_wordpress(pagina(raiz)):
                time.sleep(PAUSA)
                achados.append(ficha_wordpress(pagina(link), slug, nome))
        else:
            raise ValueError(f"modelo desconhecido: {modelo}")
    return {"base": raiz, "legislatura": None, "vereadores": achados}


def executar(limite: int | None = None) -> int:
    camaras = CAMARAS[:limite] if limite else CAMARAS
    total, falhas = 0, 0
    for ibge, url, modelo in camaras:
        try:
            camara = coletar(url, modelo)
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
                url="sites das câmaras de Pimenta Bueno, Perdões e Santa Cruz",
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
