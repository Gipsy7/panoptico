"""Assembleia Legislativa do Amazonas (ALEAM): cota parlamentar (CEAP) dos deputados, pela página
"Controle de Cota Parlamentar" do portal da transparência
(`aleam.gov.br/transparencia/controle-de-cota-parlamentar/`).

A página é um formulário (ano, mês e deputado; o seletor `dados` lista os deputados atuais com
o código de cada um) que responde, no próprio HTML, o resumo do mês (saldo anterior, verba
creditada, "Despesa Reembolsável") e a tabela das notas: beneficiário, verba, glosa e valor
líquido. Somamos o valor líquido por deputado, mês e verba, no ano anterior e no atual, e,
quando o quadro de resumo vem na resposta (nem sempre vem), conferimos a soma com a "Despesa
Reembolsável" dele. O beneficiário não é guardado.
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

FONTE = "aleam_gastos"
URL = "https://www.aleam.gov.br/transparencia/controle-de-cota-parlamentar/"
PAUSA = 0.5
SELETOR = re.compile(r'<select[^>]*name="dados"[^>]*>(?P<opcoes>.*?)</select>', re.S)
OPCAO = re.compile(r'<option value="(?P<id>\d+)"[^>]*>(?P<nome>[^<]*)</option>')
NOTA = re.compile(r'<tr data-bs-toggle="modal"[^>]*class="table-row">(?P<corpo>.*?)</tr>', re.S)
CELULA = re.compile(r"<td[^>]*>(?P<texto>.*?)</td>", re.S)
REEMBOLSAVEL = re.compile(
    r"Despesa Reembols[^<]*</span>\s*<span[^>]*>(?P<valor>[^<]*)</span>", re.S
)


def deputados(pagina: str) -> list[tuple[str, str]]:
    seletor = SELETOR.search(pagina)
    if seletor is None:
        raise ValueError("ALEAM: formulário da cota sem seletor de deputados; a página mudou.")
    return [(o["id"], base.limpo(o["nome"])) for o in OPCAO.finditer(seletor["opcoes"])]


def notas(pagina: str) -> list[tuple[str, Decimal]]:
    """(verba, valor líquido) de cada nota, conferidos com a "Despesa Reembolsável"."""
    resultado = []
    for nota in NOTA.finditer(pagina):
        celulas = [base.limpo(c["texto"]) for c in CELULA.finditer(nota["corpo"])]
        valor = gastos.valor_br(celulas[3]) if len(celulas) >= 4 else None
        if valor is None:
            raise ValueError(f"ALEAM: nota fora do formato esperado: {celulas[1:]}")
        resultado.append((comum.nome_proprio(celulas[1]) or "Sem verba na fonte", valor))
    resumo = REEMBOLSAVEL.search(pagina)
    if resumo is None:  # o quadro de resumo nem sempre vem na resposta (visto em 29/10/2026)
        return resultado
    total = gastos.valor_br(resumo["valor"]) or Decimal(0)
    soma = sum((v for _, v in resultado), Decimal(0))
    if soma != total:
        raise ValueError(f"ALEAM: notas somam {soma} e a despesa reembolsável é {total}.")
    return resultado


def baixar(client: httpx.Client, hoje: date | None = None) -> gastos.Arquivos:
    hoje = hoje or date.today()
    client.headers["Accept"] = "text/html,*/*;q=0.8"
    pagina = comum._get(client, URL, None, 4).content
    arquivos: gastos.Arquivos = {"formulario.html": pagina}
    for codigo, _nome in deputados(pagina.decode("utf-8", "replace")):
        for ano in (hoje.year - 1, hoje.year):
            for mes in range(1, 13 if ano < hoje.year else hoje.month + 1):
                gastos.pausar(PAUSA)
                resposta = client.post(URL, data={"ano": ano, "mes": f"{mes:02d}", "dados": codigo})
                arquivos[f"{codigo}_{ano}_{mes:02d}.html"] = resposta.raise_for_status().content
    return arquivos


def ler(arquivos: gastos.Arquivos) -> list[dict]:
    nomes = dict(deputados(arquivos["formulario.html"].decode("utf-8", "replace")))
    resultado = []
    for nome in sorted(arquivos):
        partes = nome.removesuffix(".html").split("_")
        if len(partes) != 3:
            continue
        codigo, ano, mes = partes
        for verba, valor in notas(arquivos[nome].decode("utf-8", "replace")):
            resultado.append(
                {"nome": nomes[codigo], "ano": int(ano), "mes": int(mes), "categoria": verba,
                 "valor": valor}
            )  # fmt: skip
    return resultado


def executar(de_raw: Path | None = None) -> int:
    return gastos.executar(
        fonte=FONTE, uf="AM", sigla="ALEAM", url=URL, baixar=baixar, ler=ler, de_raw=de_raw
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    ap.add_argument("--de-raw", type=Path, help="zip de data/raw/aleam_gastos (sem rede)")
    executar(ap.parse_args().de_raw)
