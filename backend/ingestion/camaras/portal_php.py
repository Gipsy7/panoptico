"""Câmaras municipais com o modelo de site PHP das páginas `vereadores.php` e
`papelvereador.php` (Amapá, Ferreira Gomes e Tartarugalzinho, no AP; Fortim e Poranga, no CE):
vereadores da legislatura atual com nome, nome civil, partido e foto.

O site não tem API nem dados abertos; as páginas públicas são HTML renderizado no servidor, e
o robots.txt está vazio (nada proibido). A lista (`/vereadores`, para onde `vereadores.php`
redireciona) traz um cartão por pessoa, inclusive ex-vereadores de legislaturas antigas
(Poranga lista 23 para 9 cadeiras); a ficha de cada um (`/vereadores/<id>`) diz:

- o rótulo "LEGISLATURA ATUAL - 2025/2028" (só aparece em quem tem vínculo na atual);
- a tabela "Informações dos mandatos" (cargo, vínculo, legislatura, período; o período de um
  vínculo que acabou traz "à <data>");
- o partido ("Partido: PL"), com a "Filiação partidária" como alternativa.

Está em exercício quem tem na legislatura atual um vínculo sem data de fim e que não seja de
licença; quem só teve um cargo de mesa que já acabou (visto em Fortim) fica de fora.

Fora do que o site entrega de forma estruturada: projetos (a ficha traz só as últimas
matérias), votos e presença. A página que lista as matérias é paginada e sem identificador de
autoria por linha confiável; por isso a câmara entra só com os vereadores. Uma requisição por
vez, com pausa. Grava nas mesmas tabelas do SAPL, pela gravação dele (inclusive a ligação ao
eleito do TSE).
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

FONTE = "portal_php_camaras"
SISTEMA = "portal_php"
PAUSA = 0.5
ACEITA = "text/html,application/xhtml+xml"

ID_NA_LISTA = re.compile(r'href="/vereadores/(\d+)"></a>')
LEGISLATURA_ATUAL = re.compile(r"LEGISLATURA ATUAL\s*-\s*(\d{4})\s*/\s*(\d{4})")
NOME_NA_FICHA = re.compile(r"font-weight-semibold fs-20[^>]*>(.*?)</h4>", re.S)
SUBTITULOS = re.compile(r'<h6 class="text-dark[^>]*fontesize1">(.*?)</h6>', re.S)
PARTIDO = re.compile(r"Partido:\s*([^<\n]*)")
FOTO = re.compile(r'<img src="(/imagens/[^"]+)" alt="img"')
LINHAS = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELULAS = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
PERIODO_LEGISLATURA = re.compile(r"\((\d{4})\s*-\s*(\d{4})\)")
DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def _texto(trecho: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", trecho)).split())


def ids_da_lista(pagina: str) -> list[str]:
    """Os identificadores dos cartões da lista, sem repetir e na ordem da página."""
    return list(dict.fromkeys(ID_NA_LISTA.findall(pagina)))


def _secao(pagina: str, de: str, ate: str) -> str:
    inicio = pagina.find(de)
    if inicio < 0:
        return ""
    fim = pagina.find(ate, inicio)
    return pagina[inicio : fim if fim > 0 else len(pagina)]


def _linhas(secao: str) -> list[list[str]]:
    return [
        [_texto(c) for c in CELULAS.findall(linha)]
        for linha in LINHAS.findall(secao)
        if "<td" in linha
    ]


def _data(texto: str) -> str:
    achado = DATA.search(texto)
    return f"{achado[3]}-{achado[2]}-{achado[1]}" if achado else ""


def ficha(pagina: str, base: str, id_externo: str) -> dict | None:
    """O vereador de uma ficha, ou None se não tem vínculo em exercício na legislatura atual."""
    atual = LEGISLATURA_ATUAL.search(pagina)
    if atual is None:
        return None
    inicio_leg, fim_leg = atual[1], atual[2]
    vinculos = [
        linha
        for linha in _linhas(_secao(pagina, "Informações dos mandatos", "Filiação partidária"))
        if len(linha) >= 4
        and (p := PERIODO_LEGISLATURA.search(linha[2]))
        and (p[1], p[2]) == (inicio_leg, fim_leg)
    ]
    abertos = [v for v in vinculos if "à" not in v[3].split()]
    if not abertos:
        return None
    em_exercicio = not any("LICENCIAD" in v[1].upper() for v in abertos)
    titular = not any("SUPLENTE" in (v[0] + v[1]).upper() for v in abertos)
    nome = _texto(NOME_NA_FICHA.search(pagina)[1]) if NOME_NA_FICHA.search(pagina) else ""
    subtitulos = [_texto(s) for s in SUBTITULOS.findall(pagina)]
    completo = (
        subtitulos[0]
        if subtitulos and not subtitulos[0].startswith(("Vereador", "Partido"))
        else None
    )
    achado = PARTIDO.search(pagina)
    partido = _texto(achado[1]) if achado else ""
    if not partido:  # a filiação mais recente (a tabela vai da mais antiga para a mais nova)
        filiacoes = _linhas(_secao(pagina, "Filiação partidária", "Matérias"))
        partido = filiacoes[-1][1] if filiacoes and len(filiacoes[-1]) >= 2 else ""
    foto = FOTO.search(pagina)
    return {
        "id_externo": id_externo,
        "nome": nome,
        "nome_completo": completo if completo and completo != nome else None,
        "partido": partido or None,
        "foto_url": urljoin(base, foto[1]) if foto and "semsexo" not in foto[1] else None,
        "email": None,
        "telefone": None,
        "titular": titular,
        "em_exercicio": em_exercicio,
        "inicio": min(_data(v[3]) for v in abertos),
        "fim": f"{fim_leg}-12-31",
        "proposicoes_por_tipo": {},
        "projetos": [],
    }


def coletar(url: str) -> dict:
    """Tudo o que guardamos de uma câmara, num dicionário (vira o bruto)."""
    base = url.rstrip("/")
    with comum.criar_cliente() as client:
        client.headers["Accept"] = ACEITA

        def pagina(caminho: str) -> str:
            time.sleep(PAUSA)
            return comum.get_bytes(client, f"{base}{caminho}").decode("utf-8", "replace")

        ids = ids_da_lista(pagina(""))
        vereadores = [v for i in ids if (v := ficha(pagina(f"/{i}"), base, i)) is not None]
    return {"base": base, "legislatura": None, "vereadores": vereadores}


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
                raise ValueError("nenhum vereador em exercício na legislatura atual")
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
                url="sites das câmaras do catálogo data/canais_curados.csv (modelo vereadores.php)",
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
