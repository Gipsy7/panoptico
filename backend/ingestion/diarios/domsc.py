"""Atos de nomeação, exoneração e designação no DOM/SC (Diário Oficial dos Municípios de
Santa Catarina), pelos dados abertos do CIGA.

O DOM/SC (consórcio CIGA, diariomunicipal.sc.gov.br, ~290 prefeituras e câmaras) tem
robots.txt que veda rastreadores genéricos (`User-agent: * / Disallow: /`); por isso o
site NÃO é rastreado. O mesmo consórcio publica, de forma aberta e para reúso, cada
publicação do diário em lotes ZIP de JSON no portal de dados abertos
(dados.ciga.sc.gov.br, CKAN; conjuntos mensais `domsc-publicacoes-de-MM-AAAA`, um ZIP por
dia e faixa de horário). Esse portal permite as páginas de conjunto e de download
(`/api/` é vedado e não é usado) e pede intervalo de 10 s entre requisições (Crawl-Delay),
respeitado aqui. Campos do JSON: codigo, titulo, data, municipio, entidade, categoria,
link (portal DOM/SC), texto (HTML) e url (PDF do ato).

REGRA CRÍTICA: nome encontrado em texto nunca é vínculo; o que sai daqui são SUGESTÕES em
`diario_ato` (revisado = falso) para a fila `ingestion.revisar --tipo diario`.
Recorte: últimos 90 dias na primeira carga, depois só as faixas novas; só as categorias de
ato (portarias, decretos, outras publicações, extratos, concursos, resoluções, atos da
presidência); só publicações de prefeituras e câmaras (consórcios ficam de fora); só pessoas
que já acompanhamos, no município delas. O bruto guarda só o recorte (categorias de ato).
"""

import argparse
import html
import io
import json
import re
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import DiarioAto, FonteIngestao
from ingestion import comum
from ingestion.diarios import plataformas as pl
from ingestion.diarios.atos import _sem_acento
from ingestion.diarios.revisao import aplicar_atos

FONTE = "domsc_ciga_atos"
BASE = "https://dados.ciga.sc.gov.br"
CONJUNTO = BASE + "/dataset/domsc-publicacoes-de-{mes:02d}-{ano}"
PAUSA = 10.0  # Crawl-Delay do robots.txt do portal
DIAS_PRIMEIRA_CARGA = 90
CATEGORIAS = {
    "portarias",
    "decretos",
    "outras publicacoes",
    "extratos diversos",
    "concursos",
    "resolucoes",
    "atos da presidencia",
    "atos",
}
_ZIP = re.compile(
    r'href="(https://dados\.ciga\.sc\.gov\.br/dataset/[^"]+/download/'
    r'(cigadados_publicacoes_(\d{4})_(\d{2})_(\d{2})_\d{4}_\d{4}\.zip))"'
)
# Títulos de matéria de compras, que citam o nome de quem recebe a homologação ou o contrato
# ("designada"/"nomeada" na comissão), não de ato de pessoal.
_COMPRAS = re.compile(
    r"HOMOLOGA|LICITA|PREGAO|DISPENSA|ADJUDICA|REGISTRO DE PRECO|CONTRATO|INEXIGIBILIDADE"
)
_ORGAO = re.compile(r"^(PREFEITURA|CAMARA|FUNDO|SERVICO|SAMAE|INSTITUTO|FUNDACAO|SECRETARIA)")


def listar_lotes(client: httpx.Client, desde: date, ate: date) -> list[tuple[date, str, str]]:
    """(dia, nome do ZIP, URL) dos lotes de publicações entre as datas, lendo a página de
    cada conjunto mensal."""
    meses, d = [], date(desde.year, desde.month, 1)
    while d <= ate:
        meses.append((d.year, d.month))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    lotes = []
    for ano, mes in meses:
        time.sleep(PAUSA)
        r = client.get(CONJUNTO.format(mes=mes, ano=ano), headers={"Accept": "text/html"})
        if r.status_code == 404:
            continue
        r.raise_for_status()
        for url, nome, a, m, dia in _ZIP.findall(r.text):
            data = date(int(a), int(m), int(dia))
            if desde <= data <= ate:
                lotes.append((data, nome, url))
    return sorted(set(lotes))


def recortar(payload: dict) -> list[dict[str, Any]]:
    """Publicações de prefeituras e câmaras, de categoria de ato, com município informado."""
    saida = []
    for p in payload.get("autopublicacoes") or []:
        categoria = _sem_acento(p.get("categoria") or "").lower().strip()
        entidade = _sem_acento(p.get("entidade") or "").upper().strip()
        titulo = _sem_acento(p.get("titulo") or "").upper()
        if categoria not in CATEGORIAS or not p.get("municipio") or not _ORGAO.match(entidade):
            continue
        if _COMPRAS.search(titulo):
            continue
        saida.append(
            {
                k: p.get(k)
                for k in ("codigo", "titulo", "data", "municipio", "entidade", "categoria")
            }
            | {"link": p.get("link"), "url": p.get("url"), "texto": p.get("texto")}
        )
    return saida


def texto_limpo(bruto_html: str) -> str:
    """Texto do HTML do ato (sem o cabeçalho de metadados do Tika)."""
    corpo = re.split(r"<body[^>]*>", bruto_html, maxsplit=1)[-1]
    corpo = re.sub(r"</(p|div|tr|li)>|<br\s*/?>", "\n", corpo, flags=re.I)
    texto = html.unescape(re.sub(r"<[^>]+>", " ", corpo))
    return "\n".join(" ".join(linha.split()) for linha in texto.splitlines() if linha.strip())


def processar(
    publicacoes: list[dict[str, Any]],
    indice: dict,
    alvos: dict[str, list[tuple[int, str]]],
    vistos: dict,
) -> list[dict[str, Any]]:
    resultado = []
    for p in publicacoes:
        ibge = indice.get("SC", {}).get(_sem_acento(p["municipio"]).upper().strip())
        if ibge is None:
            continue
        dia = date.fromisoformat(p["data"][:10])
        chave = ("SC", ibge)
        nome, ultima, qtd = vistos.get(chave, (p["municipio"], dia, 0))
        vistos[chave] = (nome, max(ultima, dia), qtd + 1)
        if not alvos.get(ibge):
            continue
        texto = f"{p['titulo'] or ''}\n{texto_limpo(p['texto'] or '')}"
        for pessoa_id, tipo, trecho in pl.achados_na_materia(texto, alvos[ibge]):
            resultado.append(
                {
                    "pessoa_id": pessoa_id,
                    "municipio_ibge": ibge,
                    "data": dia,
                    "tipo_ato": tipo,
                    "trecho": trecho,
                    "url": p.get("url") or p["link"],
                }
            )
    return resultado


def executar(dias: int = DIAS_PRIMEIRA_CARGA, de_raw: Path | None = None) -> int:
    hoje = date.today()
    novos = lotes_lidos = 0
    vistos: dict = {}
    with SessionLocal() as session:
        ingestao = FonteIngestao(fonte=FONTE, url=BASE, arquivo_raw="(por lote)")
        session.add(ingestao)
        session.flush()
        indice = pl.indice_municipios(session)
        alvos = pl.carregar_alvos(session, indice)
        session.commit()

        def tratar(publicacoes: list[dict[str, Any]]) -> None:
            nonlocal novos, lotes_lidos
            novos += pl.gravar_sugestoes(session, processar(publicacoes, indice, alvos, vistos))
            session.commit()
            lotes_lidos += 1

        if de_raw:
            arquivos = [de_raw] if de_raw.is_file() else sorted(de_raw.rglob("*.json.gz"))
            for arquivo in arquivos:
                tratar(pl.ler_raw_edicao(arquivo)["publicacoes"])
        else:
            pasta = comum.RAW_DIR / FONTE
            desde = hoje - timedelta(days=dias)  # lotes já guardados são pulados abaixo
            with comum.criar_cliente() as client:
                for dia, nome, url in listar_lotes(client, desde, hoje):
                    destino = pasta / f"{nome.removesuffix('.zip')}.json.gz"
                    if destino.exists() and dia < hoje - timedelta(days=2):
                        continue
                    time.sleep(PAUSA)
                    try:
                        zip_bytes = comum.get_bytes(client, url)
                        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                            payload = json.loads(z.read(z.namelist()[0]))
                    except (httpx.HTTPError, zipfile.BadZipFile, ValueError) as erro:
                        print(f"  {nome}: não lido ({erro})", flush=True)
                        continue
                    publicacoes = recortar(payload)
                    pl.gravar_raw_edicao(
                        FONTE,
                        "",
                        nome.removesuffix(".zip"),
                        {"lote": nome, "publicacoes": publicacoes},
                    )
                    tratar(publicacoes)
                    if lotes_lidos % 20 == 0:
                        print(f"  {lotes_lidos} lotes; {novos} sugestões", flush=True)
        pl.registrar_cobertura(FONTE, vistos)
        ingestao = session.merge(ingestao)
        aplicar_atos(session)
        ingestao.registros = session.scalar(select(func.count()).select_from(DiarioAto))
        ingestao.status = "ok"
        ingestao.concluido_em = datetime.now()
        session.commit()
    print(f"  {lotes_lidos} lotes; {len(vistos)} municípios vistos; {novos} sugestões")
    return novos


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    p.add_argument("--dias", type=int, default=DIAS_PRIMEIRA_CARGA)
    p.add_argument("--de-raw", type=Path, help="pasta (ou arquivo .json.gz) de bruto, sem rede")
    a = p.parse_args()
    print(f"{FONTE}: {executar(a.dias, a.de_raw)} sugestões")
