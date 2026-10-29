"""Votações nominais da Assembleia Legislativa do Ceará (ALECE), pelo portal da transparência.

- Lista: `transparencia.al.ce.gov.br/consultas-gerais/votacao-nominal/votacaoNominalcsv`, o CSV
  que a página "Votações Nominais" oferece (`LEGISLATURA;SESSÃO;MATERIA;URL`), uma linha por
  matéria votada em votação nominal, com o endereço do relatório em PDF.
- Relatório (PDF, gerado pelo painel de votação): data, resultado, processo de votação
  ("NOMINAL"), uma linha por deputado ("7 David Durand REPLUBLICANOS SIM (V)"; sem voto quando
  não votou) e o total "SIM NÃO ABSTENÇÃO BRANCO" numa linha de quatro números.

O nome e o partido vêm colados na mesma linha. Ligamos o voto ao deputado da lista de hoje cujo
nome é o começo da linha (sem acento nem pontuação), só se houver um único; nomes escritos de
outro jeito no relatório ("Antonio Henrque") ficam sem dono. Sim, não e abstenção da votação vêm
do total do próprio relatório, que conta todos os votantes. Entram as votações do ano anterior e
do atual. Este módulo só lê; quem grava é `alece.py`, junto com os deputados.
"""

import csv
import io
import re
from datetime import date
from typing import Any

from ingestion import comum

PORTAL = "https://transparencia.al.ce.gov.br"
LISTA = PORTAL + "/consultas-gerais/votacao-nominal/votacaoNominalcsv"
VOTOS = {"SIM": "Sim", "NAO": "Não", "ABSTENCAO": "Abstenção", "BRANCO": "Branco"}
LINHA = re.compile(
    r"^(?P<n>\d{1,2}) (?P<nome>.+?)(?: (?P<voto>SIM|NÃO|ABSTENÇÃO|BRANCO) \((?:V|P)\))?\s*$"
)
TOTAL = re.compile(r"^(\d+) (\d+) (\d+) (\d+)\s*$", re.M)
DATA = re.compile(r"Data:\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")
RESULTADO = re.compile(r"Resultado:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ]+)")
MATERIA_ANO = re.compile(r"^\s*\d+\s*/\s*(\d{4})")


def materias(conteudo: bytes) -> list[dict[str, str]]:
    """As linhas do CSV (legislatura, sessão, matéria e endereço do PDF)."""
    texto = conteudo.decode("utf-8-sig", errors="replace")
    return [
        {(k or "").strip(): (v or "").strip() for k, v in linha.items()}
        for linha in csv.DictReader(io.StringIO(texto), delimiter=";")
        if (linha.get("URL") or "").strip()
    ]


def recentes(linhas: list[dict[str, str]], ano_minimo: int) -> list[dict[str, str]]:
    """Matérias numeradas a partir de `ano_minimo` (o número traz o ano da matéria; o da votação
    só se sabe abrindo o PDF). Uma matéria antiga votada agora fica de fora: aceitamos, para não
    baixar e guardar a cada semana os relatórios de anos passados."""
    resultado = []
    for linha in linhas:
        m = MATERIA_ANO.match(linha.get("MATERIA", ""))
        if m is None or int(m.group(1)) >= ano_minimo:
            resultado.append(linha)
    return resultado


def texto_do_pdf(conteudo: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(conteudo)).pages)


def relatorio(texto: str) -> dict[str, Any] | None:
    """Data, resultado, totais e votos (número da linha -> (nome com partido, voto)) de um
    relatório; None se não for votação nominal ou não tiver data."""
    data = DATA.search(texto)
    if data is None or "NOMINAL" not in texto.upper():
        return None
    dia, mes, ano = (int(x) for x in data.groups())
    linhas: dict[int, tuple[str, str | None]] = {}
    for bruta in texto.splitlines():
        m = LINHA.match(bruta.strip())
        if m is None or TOTAL.match(bruta.strip()):
            continue
        voto = VOTOS.get(comum.chave_nome(m["voto"])) if m["voto"] else None
        linhas.setdefault(int(m["n"]), (m["nome"].strip(), voto))
    total = TOTAL.search(texto)
    resultado = RESULTADO.search(texto)
    return {
        "data": date(ano, mes, dia).isoformat(),
        "resultado": resultado.group(1).capitalize() if resultado else None,
        "total": tuple(int(x) for x in total.groups()) if total else None,
        "linhas": linhas,
    }


def dono(linha: str, nomes: dict[str, str]) -> str | None:
    """Código do deputado cujo nome (chave) começa a linha "Nome Partido"; só se for único."""
    chave = comum.chave_nome(linha)
    achados = {
        codigo
        for nome, codigo in nomes.items()
        if nome and (chave == nome or chave.startswith(nome + " "))
    }
    return next(iter(achados)) if len(achados) == 1 else None


def votacoes(
    lidos: list[tuple[dict[str, str], dict[str, Any]]], nomes: dict[str, str], ano_minimo: int
) -> tuple[list[dict], list[dict]]:
    """Votações (a partir de `ano_minimo`) e votos ligados aos deputados de hoje. `nomes`: chave
    do nome no site -> código (slug) do deputado."""
    lista_votacoes, lista_votos = [], []
    for linha, rel in lidos:
        if int(rel["data"][:4]) < ano_minimo:
            continue
        chave = linha["URL"].rsplit("/", 1)[-1].removesuffix(".pdf")[:20]
        votos = [(dono(nome, nomes), voto) for nome, voto in rel["linhas"].values() if voto]
        if rel["total"]:
            sim, nao, abstencoes = rel["total"][0], rel["total"][1], rel["total"][2]
        else:  # sem a linha de total, conta o que o relatório lista
            sim = sum(1 for _, v in votos if v == "Sim")
            nao = sum(1 for _, v in votos if v == "Não")
            abstencoes = sum(1 for _, v in votos if v == "Abstenção")
        lista_votacoes.append(
            {
                "id_externo": chave,
                "materia": " ".join(f"{linha['MATERIA']}".split()),
                "resultado": rel["resultado"],
                "data": rel["data"],
                "url": PORTAL + linha["URL"] if linha["URL"].startswith("/") else linha["URL"],
                "sim": sim,
                "nao": nao,
                "abstencoes": abstencoes,
            }
        )
        vistos = set()
        for codigo, voto in votos:
            if codigo and codigo not in vistos:
                vistos.add(codigo)
                lista_votos.append({"votacao": chave, "parlamentar": codigo, "voto": voto})
    return lista_votacoes, lista_votos


def baixar(client: Any, ano_minimo: int, pausa: float) -> dict[str, bytes]:
    """O CSV e os PDFs das matérias recentes (zip: `lista.csv` e `pdf/<nome>.pdf`)."""
    import time

    arquivos = {"lista.csv": comum._get(client, LISTA, None, 4).content}
    for linha in recentes(materias(arquivos["lista.csv"]), ano_minimo):
        time.sleep(pausa)
        url = PORTAL + linha["URL"] if linha["URL"].startswith("/") else linha["URL"]
        arquivos["pdf/" + linha["URL"].rsplit("/", 1)[-1]] = comum._get(
            client, url, None, 3
        ).content
    return arquivos


def ler(arquivos: dict[str, bytes]) -> list[tuple[dict[str, str], dict[str, Any]]]:
    """(linha do CSV, relatório lido) de cada PDF presente no bruto."""
    lidos = []
    for linha in materias(arquivos["lista.csv"]):
        pdf = arquivos.get("pdf/" + linha["URL"].rsplit("/", 1)[-1])
        if pdf is None:
            continue
        rel = relatorio(texto_do_pdf(pdf))
        if rel is not None:
            lidos.append((linha, rel))
    return lidos
