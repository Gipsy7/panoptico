"""Assembleia Legislativa do Espírito Santo (ALES): cota parlamentar dos gabinetes, pela página
"Cotas Parlamentares" do portal da transparência (`al.es.gov.br/Transparencia/CotasParlamentares`).

A página lista os gabinetes da legislatura ("Gab. Dep. Fulano", com o código do setor) e monta a
tabela de cada um por `Transparencia/Api/CotasParlamentaresNovoTable/{mês inicial}/{mês final}/
{ano}/{setor}/false`: por produto (diárias, passagens aéreas e, em "Reembolso das Despesas",
consultorias, divulgação, locações...), a quantidade e o valor solicitado, e o total. Pedimos mês
a mês, no ano anterior e no atual, e conferimos a soma dos produtos com o total da tabela.

O valor publicado é o "valor solicitado (reserva) ao sistema de gestão da cota" pelo gabinete,
como a própria página explica; não é necessariamente o pago. A "Devolução de diária" desconta.
Não há fornecedor. Uma requisição por vez, com pausa.
"""

import argparse
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from ingestion import comum
from ingestion.assembleias import base, gastos

FONTE = "ales_gastos"
SITE = "https://www.al.es.gov.br/"
URL = SITE + "Transparencia/CotasParlamentares"
TABELA = SITE + "Transparencia/Api/CotasParlamentaresNovoTable/{mes}/{mes}/{ano}/{setor}/false"
PAUSA = 0.3
GABINETE = re.compile(r'<option value="(?P<setor>\d+)">\s*Gab\. Dep\. (?P<nome>[^<]*)</option>')
GRADE = re.compile(r'<table id="table-grid".*?</table>', re.S)
LINHA = re.compile(r"<tr>(?P<corpo>.*?)</tr>", re.S)
CELULA = re.compile(r"<td[^>]*>(?P<texto>.*?)</td>", re.S)
DEVOLUCAO = "Devolução de diária"


def gabinetes(pagina: str) -> list[tuple[str, str]]:
    return [(g["setor"], base.limpo(g["nome"])) for g in GABINETE.finditer(pagina)]


def produtos(tabela: str) -> list[tuple[str, Decimal]]:
    """(produto, valor) de cada linha, com a devolução de diária negativa; confere com o total
    da própria tabela. Tabela sem grade ("Nenhum resultado") é vazia."""
    grade = GRADE.search(tabela)
    if grade is None:
        return []
    linhas, total = [], None
    for linha in LINHA.finditer(grade.group(0)):
        celulas = [base.limpo(c["texto"]) for c in CELULA.finditer(linha["corpo"])]
        if len(celulas) == 2 and celulas[0].startswith("Total"):
            total = gastos.valor_br(celulas[1])
        elif len(celulas) == 3:
            valor = gastos.valor_br(celulas[2]) or Decimal(0)
            linhas.append((celulas[0], -valor if celulas[0] == DEVOLUCAO else valor))
    if total is None:
        raise ValueError("ALES: tabela da cota sem total; a página mudou.")
    soma = sum((v for _, v in linhas), Decimal(0))
    if soma != total:
        raise ValueError(f"ALES: produtos somam {soma} e o total da tabela é {total}.")
    return [(p, v) for p, v in linhas if v]


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    hoje = hoje or date.today()
    client.headers["Accept"] = "text/html,*/*;q=0.8"
    pagina = comum._get(client, URL, None, 4).content
    arquivos: gastos.Arquivos = {"gabinetes.html": pagina}
    for setor, _nome in gabinetes(pagina.decode("utf-8", "replace")):
        for ano in (hoje.year - 1, hoje.year):
            for mes in range(1, 13 if ano < hoje.year else hoje.month + 1):
                gastos.pausar(PAUSA)
                url = TABELA.format(mes=mes, ano=ano, setor=setor)
                arquivos[f"{setor}_{ano}_{mes:02d}.html"] = comum._get(client, url, None, 4).content
    return arquivos


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    nomes = dict(gabinetes(arquivos["gabinetes.html"].decode("utf-8", "replace")))
    resultado = []
    for nome in sorted(arquivos):
        partes = nome.removesuffix(".html").split("_")
        if len(partes) != 3:
            continue
        setor, ano, mes = partes
        for produto, valor in produtos(arquivos[nome].decode("utf-8", "replace")):
            resultado.append(
                {"nome": nomes[setor], "ano": int(ano), "mes": int(mes), "categoria": produto,
                 "valor": valor}
            )  # fmt: skip
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="ES", sigla="ALES", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/ales_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
