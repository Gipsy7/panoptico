"""Assembleia Legislativa da Bahia (ALBA): verba indenizatória dos deputados, pela página
"Verbas indenizatórias" do site da Casa (`al.ba.gov.br/transparencia/verbas-idenizatorias`, com
o erro de grafia no endereço).

A página lista uma nota por linha (processo, número da nota, competência MM/AAAA, deputado,
categoria e valor), 20 por página, filtrada pelo ano (`?ano=AAAA&page=N`, a primeira página é
a 0). Lemos todas as páginas do ano anterior e do atual e somamos por deputado, competência e
categoria. O detalhe de cada nota (fornecedor e CPF/CNPJ) não é lido: não guardamos fornecedor.
O valor é o da listagem (o detalhe traz também a glosa; ver docs/FONTES_DE_DADOS.md).
O `robots.txt` do site não existe (404). Uma requisição por vez, com pausa.
"""

import argparse
import re
from datetime import date
from pathlib import Path

import httpx

from ingestion import comum
from ingestion.assembleias import base, gastos

FONTE = "alba_gastos"
URL = "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias"
PAUSA = 0.5
LINHA = re.compile(r'<tr class="table-itens[^"]*">(?P<corpo>.*?)</tr>', re.S)
CELULA = re.compile(r"<td[^>]*>(?P<texto>.*?)</td>", re.S)
PAGINA = re.compile(r"[?&](?:amp;)?page=(\d+)")


def notas(pagina: str) -> list[dict]:
    """Linhas da listagem: deputado, competência, categoria e valor."""
    resultado = []
    for linha in LINHA.finditer(pagina):
        celulas = [base.limpo(c["texto"]) for c in CELULA.finditer(linha["corpo"])]
        if len(celulas) < 6:
            continue
        competencia = re.fullmatch(r"(\d{1,2})/(\d{4})", celulas[2])
        valor = gastos.valor_br(celulas[5])
        if not competencia or valor is None:
            raise ValueError(f"ALBA: linha fora do formato esperado: {celulas[:6]}")
        resultado.append(
            {
                "nome": celulas[3],
                "ano": int(competencia[2]),
                "mes": int(competencia[1]),
                "categoria": celulas[4],
                "valor": valor,
            }
        )
    return resultado


def ultima_pagina(pagina: str) -> int:
    return max((int(n) for n in PAGINA.findall(pagina)), default=0)


def baixar_ano(client: httpx.Client, ano: int) -> gastos.Arquivos:
    arquivos: gastos.Arquivos = {}
    pagina, ultima = 0, 0
    while pagina <= ultima:
        gastos.pausar(PAUSA)
        resposta = comum._get(client, URL, {"ano": ano, "categoria": "", "page": pagina}, 4)
        arquivos[f"{ano}_{pagina:04d}.html"] = resposta.content
        ultima = max(ultima, ultima_pagina(resposta.text))
        pagina += 1
    return arquivos


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    hoje = hoje or date.today()
    client.headers["Accept"] = "text/html,*/*;q=0.8"
    arquivos: gastos.Arquivos = {}
    for ano in (hoje.year - 1, hoje.year):
        arquivos.update(baixar_ano(client, ano))
    return arquivos


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    resultado = []
    for nome in sorted(arquivos):
        resultado += notas(arquivos[nome].decode("utf-8", "replace"))
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="BA", sigla="ALBA", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/alba_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
