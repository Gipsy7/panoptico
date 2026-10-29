"""Assembleia Legislativa de Rondônia (ALERO): verba indenizatória (CEAP) dos deputados, pela
página "Verba Indenizatória" do portal da transparência
(`transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/`).

A página é uma busca por GET (`?categoria=&ano=AAAA&mes=M&gabinete=ID`, todos os filtros
obrigatórios; o seletor `gabinete` lista os deputados atuais, "DEPUTADO FULANO"). A resposta traz,
por lote do mês, um título ("... - Lote: Principal - Verbas Gerais - Total pago: R$ X") e uma
linha por nota (prestador, classe, data e valor). Somamos o valor por deputado, mês e classe, no
ano anterior e no atual, e conferimos a soma de cada lote com o "Total pago" do título (quando
as notas listadas somam menos, a diferença entra numa linha própria; ver `notas`). O
prestador (pode ser pessoa física; a página mascara o CPF) não é guardado.
O `robots.txt` libera a página. Uma requisição por vez, com pausa.
"""

import argparse
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from ingestion import comum
from ingestion.assembleias import base, gastos

FONTE = "alero_gastos"
URL = "https://transparencia.al.ro.leg.br/Deputados/VerbaIndenizatoria/"
PAUSA = 0.5
SELETOR = re.compile(r"<select[^>]*id=\"gabinete\"[^>]*>(?P<opcoes>.*?)</select>", re.S)
OPCAO = re.compile(r'<option value="(?P<id>\d+)"[^>]*>(?P<nome>[^<]*)</option>')
TABELA = re.compile(r'<table id="tabela".*?</table>', re.S)
CELULA = re.compile(r"<td[^>]*>(?P<texto>.*?)</td>", re.S)
TITULO = re.compile(r"Lote:[^-]*-\s*(?P<verba>[^-]*?)\s*-\s*Total pago:\s*(?P<total>R\$\s*[\d.,]+)")
NOTA = re.compile(r"Valor:\s*(?P<valor>R\$\s*-?[\d.,]+)")
SEM_DETALHE = "Pago sem nota listada na página (diferença para o total pago do lote)"
CLASSE = re.compile(r"Classe:\s*(?P<classe>[^|]*)\|")


def deputados(pagina: str) -> list[tuple[str, str]]:
    seletor = SELETOR.search(pagina)
    if seletor is None:
        raise ValueError("ALERO: busca da verba sem seletor de gabinete; a página mudou.")
    return [
        (o["id"], re.sub(r"^DEPUTAD[OA]\s+", "", base.limpo(o["nome"]), flags=re.I))
        for o in OPCAO.finditer(seletor["opcoes"])
    ]


def notas(pagina: str) -> list[tuple[str, Decimal]]:
    """(classe, valor) de cada nota. Cada lote é conferido com o "Total pago" do título: a
    página às vezes lista notas que somam menos que o total pago (13 de ~600 páginas em
    29/10/2026); a diferença entra numa linha própria (`SEM_DETALHE`), para o total ser o pago
    que a Casa publica. Notas que somam mais que o total abortam a carga."""
    tabela = TABELA.search(pagina)
    if tabela is None:
        return []
    resultado: list[tuple[str, Decimal]] = []
    lotes: list[tuple[Decimal, Decimal]] = []  # (total do título, soma das notas)
    verba = ""
    for celula in CELULA.finditer(tabela.group(0)):
        texto = base.limpo(celula["texto"])
        titulo, nota = TITULO.search(texto), NOTA.search(texto)
        if titulo:
            lotes.append((gastos.valor_br(titulo["total"]) or Decimal(0), Decimal(0)))
            verba = titulo["verba"]
        elif nota:
            valor = gastos.valor_br(nota["valor"]) or Decimal(0)
            if not lotes:  # visto só com valor zero, antes do primeiro título
                if valor:
                    raise ValueError("ALERO: nota com valor antes do título do lote.")
                continue
            lotes[-1] = (lotes[-1][0], lotes[-1][1] + valor)
            # As notas das "Verbas de Saúde" vêm só com data e valor, sem prestador nem classe.
            classe = CLASSE.search(texto)
            rotulo = classe["classe"] if classe else verba or "Sem classe na fonte"
            resultado.append((" ".join(rotulo.split()).capitalize(), valor))
    for total, soma in lotes:
        if soma > total:
            raise ValueError(f"ALERO: notas do lote somam {soma} e o total pago é {total}.")
        if soma < total:
            resultado.append((SEM_DETALHE, total - soma))
    return [(c, v) for c, v in resultado if v]


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    hoje = hoje or date.today()
    client.headers["Accept"] = "text/html,*/*;q=0.8"
    pagina = comum._get(client, URL, None, 4).content
    arquivos: gastos.Arquivos = {"busca.html": pagina}
    for codigo, _nome in deputados(pagina.decode("utf-8", "replace")):
        for ano in (hoje.year - 1, hoje.year):
            for mes in range(1, 13 if ano < hoje.year else hoje.month + 1):
                gastos.pausar(PAUSA)
                params = {"categoria": "", "ano": ano, "mes": mes, "gabinete": codigo}
                arquivos[f"{codigo}_{ano}_{mes:02d}.html"] = comum._get(
                    client, URL, params, 4
                ).content
    return arquivos


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    nomes = dict(deputados(arquivos["busca.html"].decode("utf-8", "replace")))
    resultado = []
    for nome in sorted(arquivos):
        partes = nome.removesuffix(".html").split("_")
        if len(partes) != 3:
            continue
        codigo, ano, mes = partes
        for classe, valor in notas(arquivos[nome].decode("utf-8", "replace")):
            resultado.append(
                {"nome": nomes[codigo], "ano": int(ano), "mes": int(mes), "categoria": classe,
                 "valor": valor}
            )  # fmt: skip
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="RO", sigla="ALERO", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/alero_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
