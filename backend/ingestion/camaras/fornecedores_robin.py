"""Câmaras que trocaram o SAPL por sites de fornecedores com poucas câmaras: um leitor pequeno por
modelo de página, na mesma carga. Vereadores da legislatura 2025–2028 (nome, nome completo,
partido, foto, id), gravados nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação
ao eleito do TSE).

- `wix` (Senador Guiomard, AC): o site da câmara é feito no Wix e a página `/vereadores` já vem
  com os cartões no HTML (nome civil e, entre parênteses, o apelido; cargo; partido; link da
  ficha). Uma requisição. O `robots.txt` só pede espera a bots de SEO.
- `esolution` (Praia Grande, SP): o site é a "onepage" do e-Solution (IPM), montada no navegador
  a partir de um JSON público, `/publico/service/onepage/select.geral.bandeiras.php`, o mesmo que
  a página chama. O bloco "VEREADORES" traz um item por vereador em atividade (nome, link da
  ficha, partido). O `robots.txt` veta `/datafiles/`, onde ficam as fotos: por isso a foto não é
  guardada. Uma requisição.

Ficam de fora (ver `data/pendencias_cobertura.csv`) as câmaras cuja lista de vereadores não está
legível: Carolina (MA) e Garopaba (SC) e Itatuba (PB) e São Raimundo das Mangabeiras (MA).
Imbuia (SC) e Campos Belos (GO) já têm leitor (`portal_modelo` e `nucleogov`). Projetos, votos e
presença não são coletados.
"""

import argparse
import html
import json
import re
import time
from datetime import UTC, datetime
from urllib.parse import unquote, urljoin

from app.db import SessionLocal
from app.models import FonteIngestao
from ingestion import comum
from ingestion.camaras import sapl

FONTE = "fornecedores_robin_camaras"
ACEITA = "text/html,application/xhtml+xml,application/json"
LEGISLATURA = ("2025-01-01", "2028-12-31")
PAUSA = 5.0

# (código IBGE, endereço da câmara, leitor)
CAMARAS = (
    ("1200450", "https://www.senadorguiomard.ac.leg.br", "wix"),
    ("3541000", "https://www.praiagrande.sp.leg.br", "esolution"),
)

PARTIDOS = {"UNIÃO BRASIL": "UNIÃO", "UNIAO BRASIL": "UNIÃO"}


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def _partido(texto: str | None) -> str | None:
    texto = _texto(texto or "")
    if texto[1:].islower() and texto[:1].isupper():  # "Republicanos" -> "REPUBLICANOS"
        texto = texto.upper()
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


# --- Wix (Senador Guiomard) ---------------------------------------------------------------

ITEM_WIX = re.compile(r'wixui-repeater__item"')
NOME_WIX = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
TEXTO_WIX = re.compile(r'<p class="font_8[^>]*>(.*?)</p>', re.S)
LINK_WIX = re.compile(r'href="[^"]*/vereadores/([^"/?#]+)"')
FOTO_WIX = re.compile(r'<img src="(https://static\.wixstatic\.com/media/[^"]+)"')


def vereadores_wix(pagina: str) -> list[dict]:
    """Um cartão por vereador: nome civil (com o apelido entre parênteses), cargo e partido."""
    achados = []
    for trecho in ITEM_WIX.split(pagina)[1:]:
        link, nome = LINK_WIX.search(trecho), NOME_WIX.search(trecho)
        textos = [_texto(t) for t in TEXTO_WIX.findall(trecho)]
        if not link or not nome or len(textos) < 2:
            continue  # outro bloco repetido da página (menu, notícias)
        civil = _texto(nome[1])
        apelido = re.fullmatch(r"(.*?)\s*\((.+)\)", civil)
        completo, nome_urna = (apelido[1], apelido[2]) if apelido else (None, civil)
        foto = FOTO_WIX.search(trecho)
        if foto and "empty-state" in foto[1]:  # imagem padrão do Wix, sem foto cadastrada
            foto = None
        achados.append(
            _vereador(
                unquote(link[1]),
                nome_urna,
                completo,
                _partido(textos[1]),
                foto[1] if foto else None,
            )
        )
    return achados


# --- e-Solution (Praia Grande) ------------------------------------------------------------

BLOCO_VEREADORES = "VEREADORES"


def vereadores_esolution(pagina: str) -> list[dict]:
    """Os itens do bloco 'VEREADORES' do JSON da onepage: nome, link da ficha e partido."""
    achados = []
    for bloco in json.loads(pagina).get("bandeiras", []):
        if bloco.get("ban_nome", "").strip().upper() != BLOCO_VEREADORES:
            continue
        for item in bloco.get("filhos", []):
            if item.get("ban_ativo") != "1" or not item.get("ban_nome"):
                continue
            achados.append(
                _vereador(
                    item["ban_codigo"],
                    _texto(item["ban_nome"]),
                    None,
                    _partido(item.get("ban_texto")),
                )  # fmt: skip
            )
    return achados


# --- Coleta -------------------------------------------------------------------------------


def _pagina(client, url: str) -> str:
    return comum.get_bytes(client, url).decode("utf-8", "replace")


def coletar(url: str, leitor: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    raiz = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA
        if leitor == "wix":
            base = raiz + "/vereadores"
            achados = vereadores_wix(_pagina(client, base))
        elif leitor == "esolution":
            base = urljoin(raiz + "/", "publico/service/onepage/select.geral.bandeiras.php")
            achados = vereadores_esolution(_pagina(client, base))
        else:
            raise ValueError(f"leitor desconhecido: {leitor}")
    return {"base": base, "legislatura": None, "vereadores": achados}


def executar(limite: int | None = None) -> int:
    camaras = CAMARAS[:limite] if limite else CAMARAS
    total, falhas = 0, 0
    for ibge, url, leitor in camaras:
        try:
            camara = coletar(url, leitor)
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
                url="sites das câmaras de Senador Guiomard (Wix) e Praia Grande (e-Solution)",
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
