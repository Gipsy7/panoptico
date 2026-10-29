"""Assembleia Legislativa da Paraíba (ALPB): verba indenizatória (VIAP) dos deputados, pela
página "VIAP" do portal da transparência (`al.pb.leg.br/transparencia/deputados/viap-v2`).

A página pede ano, mês e gabinete (`?tipo_viap=deputados&ano_viap=AAAA&mes_viap=M&deputado=ID`;
o seletor `deputado` lista os gabinetes) e responde com o link da planilha de prestação de
contas do mês (ODS em 2025, XLSX em 2026, dentro de um link do visualizador do Office; as
colunas mudam entre os dois, achamos pelo cabeçalho). A planilha traz uma linha por despesa
(competência, deputado, item, subitem,
fornecedor, CPF/CNPJ mascarado, data, documento e valor) e as linhas de resumo ("Saldo
Anterior", "Crédito", "Total de Despesas", "Reembolso"). Somamos por gabinete, mês e subitem, no
ano anterior e no atual, e conferimos a soma com o "Total de Despesas" da própria planilha.
O nome que ligamos ao deputado é o do seletor (nome parlamentar), não o civil da planilha.
Fornecedor e CPF/CNPJ não são guardados. O `robots.txt` só veda `/wp-admin/`.
Uma requisição por vez, com pausa.
"""

import argparse
import html
import io
import re
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree

import httpx

from ingestion import comum
from ingestion.assembleias import base, gastos

FONTE = "alpb_gastos"
URL = "https://www.al.pb.leg.br/transparencia/deputados/viap-v2"
PAUSA = 0.5
SELETOR = re.compile(r'<select name="deputado"[^>]*>(?P<opcoes>.*?)</select>', re.S)
OPCAO = re.compile(
    r"<option\s+(?:selected='selected'\s+)?value='(?P<id>\d+)'>(?P<nome>[^<]*)</option>"
)
LINK = re.compile(r"<ul class='lista-v[^']*'[^>]*>.*?href='(?P<href>[^']+)'", re.S)
XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ODS_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODS_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODS_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"


def gabinetes(pagina: str) -> list[tuple[str, str]]:
    seletor = SELETOR.search(pagina)
    if seletor is None:
        raise ValueError("ALPB: página da VIAP sem seletor de gabinete; a página mudou.")
    return [(o["id"], base.limpo(o["nome"])) for o in OPCAO.finditer(seletor["opcoes"])]


def link_da_planilha(pagina: str) -> str | None:
    """O endereço da planilha do mês, tirado do link do visualizador do Office (`?src=`)."""
    achado = LINK.search(pagina)
    if achado is None:
        return None
    href = html.unescape(achado["href"])
    src = parse_qs(urlparse(href).query).get("src")
    return unquote(src[0]) if src else href


def _coluna(ref: str) -> int:
    n = 0
    for letra in re.sub(r"\d", "", ref):
        n = n * 26 + ord(letra) - 64
    return n - 1


def grade_xlsx(conteudo: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        textos = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ElementTree.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{XLSX}si"):
                textos.append("".join(t.text or "" for t in si.iter(f"{XLSX}t")))
        folha = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    linhas = []
    for linha in folha.iter(f"{XLSX}row"):
        valores: dict[int, str] = {}
        for c in linha.iter(f"{XLSX}c"):
            v = c.find(f"{XLSX}v")
            texto = (v.text or "") if v is not None else ""
            if v is None:
                texto = "".join(t.text or "" for t in c.iter(f"{XLSX}t"))
            elif c.get("t") == "s" and texto:
                texto = textos[int(texto)]
            valores[_coluna(c.get("r", "A"))] = texto.strip()
        linhas.append([valores.get(i, "") for i in range(max(valores, default=-1) + 1)])
    return linhas


def grade_ods(conteudo: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        raiz = ElementTree.fromstring(z.read("content.xml"))
    tabela = next(raiz.iter(f"{ODS_TABLE}table"))
    linhas = []
    for linha in tabela.iter(f"{ODS_TABLE}table-row"):
        valores: list[str] = []
        for c in linha:
            if c.tag not in (f"{ODS_TABLE}table-cell", f"{ODS_TABLE}covered-table-cell"):
                continue
            repete = min(int(c.get(f"{ODS_TABLE}number-columns-repeated", "1")), 50)
            numero = c.get(f"{ODS_OFFICE}value")
            texto = (
                numero
                if numero is not None
                else " ".join("".join(p.itertext()) for p in c.iter(f"{ODS_TEXT}p"))
            )
            valores += [texto.strip()] * repete
        while valores and not valores[-1]:
            valores.pop()
        linhas.append(valores)
    return linhas


def grade(conteudo: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nomes = z.namelist()
    return grade_ods(conteudo) if "content.xml" in nomes else grade_xlsx(conteudo)


def _valor(texto: str) -> Decimal | None:
    """Número da célula: '9000' / '9063.48' (valor numérico) ou '9.000,00' (texto)."""
    texto = texto.strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", texto):
        return Decimal(texto).quantize(Decimal("0.01"))
    return gastos.valor_br(texto)


def despesas(conteudo: bytes) -> list[tuple[str, Decimal]]:
    """(subitem, valor) de cada despesa, conferidos com o "Total de Despesas" da planilha."""
    linhas = grade(conteudo)
    cab = next((i for i, lin in enumerate(linhas) if "SUB_ITEM" in [c.upper() for c in lin]), None)
    if cab is None:
        raise ValueError("ALPB: planilha sem cabeçalho (SUB_ITEM); o formato mudou.")
    colunas = {c.upper(): i for i, c in enumerate(linhas[cab]) if c}
    sub, val = colunas["SUB_ITEM"], colunas["VALOR"]
    resultado, total = [], None
    for lin in linhas[cab + 1 :]:
        celulas = lin + [""] * (max(colunas.values()) + 1 - len(lin))
        resumo = " ".join(celulas).upper()
        if "TOTAL DE DESPESAS" in resumo:
            # o valor do resumo fica na última célula preenchida da linha
            total = _valor(next(c for c in reversed(celulas) if c))
        elif celulas[sub] and not re.search(r"=>", resumo):
            valor = _valor(celulas[val])
            if valor is None:
                raise ValueError(f"ALPB: despesa sem valor legível: {celulas[sub]}")
            resultado.append((" ".join(celulas[sub].split()), valor))
    soma = sum((v for _, v in resultado), Decimal(0))
    if total is None or soma != total:
        raise ValueError(f"ALPB: despesas somam {soma} e o total da planilha é {total}.")
    return resultado


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    """Por ano, a página do mês 1 (o seletor de gabinetes só vem com ano e mês escolhidos e
    muda com a composição) e, por gabinete e mês, a página e a planilha."""
    hoje = hoje or date.today()
    client.headers["Accept"] = "text/html,*/*;q=0.8"
    arquivos: gastos.Arquivos = {}
    for ano in (hoje.year - 1, hoje.year):
        params = {"tipo_viap": "deputados", "ano_viap": ano, "mes_viap": 1}
        pagina = comum._get(client, URL, params, 4).content
        arquivos[f"gabinetes_{ano}.html"] = pagina
        for codigo, _nome in gabinetes(pagina.decode("utf-8", "replace")):
            for mes in range(1, 13 if ano < hoje.year else hoje.month + 1):
                gastos.pausar(PAUSA)
                params = {"tipo_viap": "deputados", "ano_viap": ano, "mes_viap": mes,
                          "deputado": codigo}  # fmt: skip
                resposta = comum._get(client, URL, params, 4).content.decode("utf-8", "replace")
                link = link_da_planilha(resposta)
                if link is None:
                    continue
                gastos.pausar(PAUSA)
                arquivos[f"{codigo}_{ano}_{mes:02d}.planilha"] = comum._get(
                    client, link, None, 4
                ).content
    return arquivos


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    nomes: dict[str, str] = {}
    for nome in sorted(arquivos):
        if nome.startswith("gabinetes_"):
            nomes.update(gabinetes(arquivos[nome].decode("utf-8", "replace")))
    resultado = []
    for nome in sorted(arquivos):
        if not nome.endswith(".planilha"):
            continue
        codigo, ano, mes = nome.removesuffix(".planilha").split("_")
        for subitem, valor in despesas(arquivos[nome]):
            resultado.append(
                {"nome": nomes[codigo], "ano": int(ano), "mes": int(mes), "categoria": subitem,
                 "valor": valor}
            )  # fmt: skip
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="PB", sigla="ALPB", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/alpb_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
