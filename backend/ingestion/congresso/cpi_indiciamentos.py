"""SUGESTÕES de indiciamento extraídas dos relatórios finais de CPIs (tabela
`cpi_indiciamento_sugestao`). Nada aqui é publicável.

Por quê: pedido de indiciamento num relatório de CPI não é acusação formal nem condenação, e
um nome achado em texto de PDF não é vínculo com uma pessoa (homônimos). Regras do projeto
(docs/DECISOES.md): presunção de inocência, só documento oficial, nome em texto nunca liga
automaticamente. Por isso a extração só produz uma fila de revisão: o nome como está no
relatório, o trecho, a página e o link do PDF, com `revisado = false` e sem `pessoa_id`.
O próximo passo (não feito) é uma fila de revisão como a de `ingestion.revisar --tipo diario`:
uma pessoa confere o trecho, liga o nome a uma pessoa por chave forte e só então um evento
(descrevendo o ato: "citado em pedido de indiciamento no relatório final da CPI X, em tal
data, sem que isso signifique denúncia ou condenação") pode ser gerado.

Só entram relatórios adotados pela comissão: na Câmara, CPIs com situação "Parecer
aprovado" (relatório do relator rejeitado ou sem votação não é conclusão da CPI); no Senado
e no Congresso, relatórios cujo rótulo diz "aprovado". Os PDFs do Senado
(legis.senado.leg.br/sdleg-getter) às vezes respondem com uma verificação de segurança com
prova de trabalho no navegador; não a contornamos (docs/DECISOES.md, escada de acesso): se a
resposta não for um PDF, a CPI é pulada e registrada como bloqueada. Com o PDF baixado à mão,
use `--pdf arquivo.pdf --cpi casa:id`.

Formatos reconhecidos, sob um título que termine em "indiciamento(s)": lista numerada
("3) Fabio Schvartsman: art. ..." na CPI de Brumadinho; "1) JAIR MESSIAS BOLSONARO – cargo"
na CPI da Pandemia) e marcadores com nomes em maiúsculas ("• EMÍLIO ALVES ODEBRECHT, pela
prática dos crimes..." na CPI do BNDES). Outros formatos ficam com 0 sugestões, para revisão
manual. Citados "para aprofundar a investigação" não são pedidos de indiciamento e, na lista
numerada, não entram; nos marcadores o relatório mistura "indiciamento e aprofundamento", e
quem revisa decide pelo trecho e pela página. O nome vem como o PDF o extrai, inclusive com
espaços no meio de palavras ("Figueir edo"): a revisão corrige.
"""

import argparse
import re
import time
from pathlib import Path
from typing import Any

import httpx
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Cpi, CpiIndiciamentoSugestao, FonteIngestao
from ingestion import comum

FONTE = "cpi_indiciamentos"
JANELA = 40  # páginas lidas a partir do título da seção
PRIMEIRAS_PAGINAS_IGNORADAS = 10  # sumário e apresentação
TRECHO_MAXIMO = 600
# Linha curta (sem ponto no meio) que termina em "indiciamento(s)": "10.4.3 Sugestão de
# indiciamentos", "13.27 Resumo dos indiciamentos", "12.2.1 ...: sugestões de indiciamento".
TITULO = re.compile(
    r"^[ \t]*(?:\d+(?:\.\d+)*\.?[ \t]+)?[^\n.]{0,70}?\bindiciament\w*[ \t]*$", re.I | re.M
)
NUMERO_TITULO = re.compile(r"^[ \t]*(\d+(?:\.\d+)*)\.?[ \t]+\S")
PROXIMO_TITULO = re.compile(r"^[ \t]*(\d+(?:\.\d+)+)\.?[ \t]+[A-ZÀ-Ý]", re.M)
# "3) Fabio Schvartsman: art. 121..." / "1) JAIR MESSIAS BOLSONARO – Presidente..." (itens
# numerados de 1 em diante, sem pular número)
ITEM = re.compile(
    r"(?:(?<=\s)|^)(\d{1,3})\s*[).]\s+([A-ZÀ-Ý][^:;–—()]{1,100}?)(?=\s*(?::\s|[–—]\s|\s-\s|,\s))"
)
# "<marcador> EMÍLIO ALVES ODEBRECHT, pela prática dos crimes...": marcador de lista (o do
# PDF do relatório é \uf0b7, da fonte Symbol) e nomes em maiúsculas, separados por vírgula
# ou "E", seguidos da conduta.
MARCADOR = "\uf0b7•●▪◦"
NOME_MAIUSCULO = r"[A-ZÀ-Ý][A-ZÀ-Ý'’.\-]*"
ITEM_MARCADOR = re.compile(
    rf"[{MARCADOR}]\s*({NOME_MAIUSCULO}(?:[ ,]+{NOME_MAIUSCULO})*)\s*,\s+"
    rf"(?=[^{MARCADOR}]{{0,200}}?(?:pel[ao]s?\s+pr[áa]tica|crimes?|condi[çc][ãa]o|corrup))"
)
NAO_NOME = re.compile(r"^(art|inc|lei|decreto|§|cpi|cpmi)\b", re.I)
EMPRESA = re.compile(
    r"\b(S\.?\s?A\.?|L\s?tda\.?|Eireli|EPP|Companhia|Empresa|Bureau|Consultoria|"
    r"Corporation|Inc\.?|Group|Grupo|Associa[çc][ãa]o|Instituto|Funda[çc][ãa]o|Banco)(?!\w)",
    re.I,
)


def _normal(texto: str) -> str:
    """Espaços simples e o marcador da fonte Symbol (caractere privado do PDF) como "•"."""
    return " ".join((texto or "").replace("\uf0b7", "•").split())


def _fim_da_secao(corpo: str, profundidade: int) -> int | None:
    """Posição do próximo título numerado do mesmo nível (ou acima) do título de indiciamento;
    subseções (níveis mais fundos) continuam dentro da seção. Sem número, não há corte."""
    if not profundidade:
        return None
    for m in PROXIMO_TITULO.finditer(corpo):
        if m.group(1).count(".") + 1 <= profundidade:
            return m.start()
    return None


def _janelas(paginas: list[str]) -> list[list[tuple[int, str]]]:
    """Para cada título de "indiciamento(s)" fora do sumário: as páginas seguintes (JANELA)
    como [(número da página, texto)], começando depois do título e cortadas no próximo título
    numerado (ex.: "12.2.2 Rescisão de acordos")."""
    janelas = []
    for i, texto in enumerate(paginas):
        if i < PRIMEIRAS_PAGINAS_IGNORADAS:
            continue
        for m in TITULO.finditer(texto):
            if "...." in m.group(0):
                continue
            numero = NUMERO_TITULO.match(m.group(0))
            profundidade = numero.group(1).count(".") + 1 if numero else 0
            janela, resto = [], texto[m.end() :]
            for n in range(i, min(i + JANELA, len(paginas))):
                corpo = resto if n == i else paginas[n]
                corte = _fim_da_secao(corpo, profundidade)
                janela.append((n + 1, corpo[:corte] if corte is not None else corpo))
                if corte is not None:
                    break
            janelas.append(janela)
    return janelas


def _texto_e_paginas(janela: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int]]]:
    texto, inicios = "", []
    for numero, pagina in janela:
        inicios.append((len(texto), numero))
        texto += _normal(pagina) + " "
    return texto, inicios


def _itens_numerados(texto: str) -> list[tuple[int, int, str]]:
    """(início, fim, nome) dos itens 1, 2, 3... em sequência."""
    achados, esperado = [], 1
    for m in ITEM.finditer(texto):
        if int(m.group(1)) == esperado and not NAO_NOME.match(m.group(2)):
            achados.append(m)
            esperado += 1
    if len(achados) < 2:
        return []
    return [
        (m.start(), achados[i + 1].start() if i + 1 < len(achados) else len(texto), m.group(2))
        for i, m in enumerate(achados)
    ]


def _itens_marcador(texto: str) -> list[tuple[int, int, str]]:
    itens = []
    for m in ITEM_MARCADOR.finditer(texto):
        proximo = texto.find(texto[m.start()], m.end())  # o próximo item com o mesmo marcador
        fim = proximo if proximo != -1 else len(texto)
        partes = [p for p in re.split(r"\s*,\s*", m.group(1)) if p.strip()]
        if len(partes) > 1:  # "X, Y E Z": o "E" só separa nomes no fim de uma lista
            partes = partes[:-1] + re.split(r"\s+E\s+", partes[-1])
        for parte in partes:
            nome = parte.strip(" .,;")
            if len(nome.split()) >= 2 and not NAO_NOME.match(nome):
                itens.append((m.start(), fim, nome))
    return itens


def sugestoes_do_texto(paginas: list[str]) -> list[dict[str, Any]]:
    """Nomes dos pedidos de indiciamento: de cada título de indiciamento, o formato (lista
    numerada ou marcadores) que render mais itens. Nome como está no relatório, trecho do
    item e página onde começa."""
    melhor: list[dict[str, Any]] = []
    for janela in _janelas(paginas):
        texto, inicios = _texto_e_paginas(janela)
        itens = max(_itens_numerados(texto), _itens_marcador(texto), key=len)
        resultado, vistos = [], set()
        for inicio, fim, nome in itens:
            nome = nome.strip(" .,;")[:200]
            if nome.lower() in vistos:
                continue
            vistos.add(nome.lower())
            resultado.append(
                {
                    "nome_citado": nome,
                    "pessoa_juridica": bool(EMPRESA.search(nome)),
                    "trecho": texto[inicio : min(fim, inicio + TRECHO_MAXIMO)].strip(),
                    "pagina": [n for p, n in inicios if p <= inicio][-1],
                }
            )
        if len(resultado) > len(melhor):
            melhor = resultado
    return melhor


def paginas_do_pdf(caminho: Path) -> list[str]:
    leitor = PdfReader(str(caminho))
    paginas = []
    for pagina in leitor.pages:
        try:
            paginas.append(pagina.extract_text() or "")
        except Exception:  # página com fonte quebrada não derruba o relatório inteiro
            paginas.append("")
    return paginas


def e_pdf(caminho: Path) -> bool:
    with caminho.open("rb") as f:
        return f.read(5) == b"%PDF-"


def elegivel(cpi: Cpi) -> bool:
    if not cpi.relatorio_url:
        return False
    if cpi.casa == "camara":
        return (cpi.situacao or "") == "Parecer aprovado"
    return "aprovad" in (cpi.relatorio_rotulo or "").lower()


def processar(client: httpx.Client, cpi: dict, pdf: Path | None = None) -> dict:
    """Baixa (ou lê) o PDF do relatório e extrai as sugestões. Nunca levanta por causa do PDF."""
    resultado = {**cpi, "sugestoes": [], "status": "ok", "paginas": 0}
    baixado = None
    try:
        if pdf is None:
            baixado = comum.baixar_para_arquivo(client, cpi["url"], tentativas=3)
            pdf = baixado
        if not e_pdf(pdf):
            resultado["status"] = "bloqueado: a resposta não é um PDF (verificação de segurança)"
            return resultado
        paginas = paginas_do_pdf(pdf)
        resultado["paginas"] = len(paginas)
        if not any(p.strip() for p in paginas):
            resultado["status"] = "sem texto extraível (PDF escaneado)"
            return resultado
        resultado["sugestoes"] = sugestoes_do_texto(paginas)
        if not resultado["sugestoes"]:
            resultado["status"] = "sem seção de indiciamentos reconhecida"
    except httpx.HTTPError as erro:
        resultado["status"] = f"erro de rede: {erro.__class__.__name__}"
    finally:
        if baixado is not None:
            baixado.unlink(missing_ok=True)
    return resultado


def gravar(session: Session, resultados: list[dict]) -> int:
    """Troca as sugestões ainda não revisadas de cada CPI; as já revisadas ficam."""
    total = 0
    for r in resultados:
        cpi_id = session.scalar(
            select(Cpi.id).where(Cpi.casa == r["casa"], Cpi.id_externo == r["id_externo"])
        )
        if cpi_id is None or not r["sugestoes"]:
            continue
        session.execute(
            delete(CpiIndiciamentoSugestao).where(
                CpiIndiciamentoSugestao.cpi_id == cpi_id,
                CpiIndiciamentoSugestao.revisado.is_(False),
            )
        )
        for s in r["sugestoes"]:
            session.execute(
                pg_insert(CpiIndiciamentoSugestao)
                .values(**s, cpi_id=cpi_id, url=r["url"], revisado=False)
                .on_conflict_do_nothing(index_elements=["cpi_id", "nome_citado"])
            )
            total += 1
    return total


def executar(
    siglas: list[str] | None = None,
    de_raw: Path | None = None,
    pdf: Path | None = None,
    cpi: str | None = None,
) -> int:
    def baixar(client: httpx.Client) -> list[dict]:
        with comum.SessionLocal() as session:
            cpis = [c for c in session.scalars(select(Cpi).order_by(Cpi.id)) if elegivel(c)]
        if cpi:
            casa, _, id_externo = cpi.partition(":")
            cpis = [c for c in cpis if (c.casa, c.id_externo) == (casa, id_externo)]
            if not cpis:
                raise SystemExit(f"CPI {cpi} não encontrada ou sem relatório elegível")
        if siglas:
            cpis = [c for c in cpis if c.sigla in siglas]
        resultados = []
        for c in cpis:
            print(f"  {c.sigla}: {c.relatorio_url}", flush=True)
            time.sleep(1)
            alvo = {"casa": c.casa, "id_externo": c.id_externo, "sigla": c.sigla}
            r = processar(client, {**alvo, "url": c.relatorio_url}, pdf)
            print(f"    {r['paginas']} páginas; {len(r['sugestoes'])} sugestões; {r['status']}")
            resultados.append(r)
        return resultados

    def carregar(session: Session, payload: list[dict], ingestao: FonteIngestao) -> int:
        return gravar(session, payload)

    url = "https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra"
    return comum.executar_ingestao(FONTE, url, baixar, carregar, de_raw=de_raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--sigla", nargs="*", help="Só estas CPIs (ex.: CPIBRUMA CPIBNDES)")
    parser.add_argument("--pdf", type=Path, help="PDF já baixado (com --cpi)")
    parser.add_argument("--cpi", help="casa:id_externo da CPI do PDF (ex.: senado:2441)")
    parser.add_argument("--de-raw", type=Path, help="Reprocessa um arquivo bruto")
    args = parser.parse_args()
    print(f"{FONTE}: {executar(args.sigla, args.de_raw, args.pdf, args.cpi)} sugestões gravadas")
