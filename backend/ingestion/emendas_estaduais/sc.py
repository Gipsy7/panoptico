"""Emendas impositivas da ALESC (Santa Catarina), pelo SC Transferências da CGE/SC.

Fonte: a "Pesquisa detalhada > Emendas" do SC Transferências
(consultas.sctransferencias.cge.sc.gov.br) tem um botão "Baixar CSV" que chama
`sctransf-api.prod.okd4.ciasc.sc.gov.br/csv/emendas`: sem filtro, devolve todas as emendas
com proposta no sistema (2022 em diante), uma linha por **proposta** de transferência
(convênio, termo de fomento ou de colaboração), com deputado ou bancada autora, beneficiário
(nome e CNPJ), município do beneficiário, órgão concedente, valor da emenda na Lei
Orçamentária e valor repassado. A página "Dados abertos" do mesmo sistema publica, por ano, o
razão financeiro das transferências (`dados_financeiros_AAAA.zip`: empenhos, liquidações e
pagamentos, com anulações e estornos em valor negativo); dele sai o valor empenhado de cada
transferência. Tudo público, sem login nem captcha; uma requisição por vez, com pausa.

Armadilhas (vistas na amostra de 19/10/2026):
- o número da emenda se repete: uma emenda pode ter várias propostas (refeita, cancelada,
  dividida). A chave é a proposta; o valor previsto só se soma uma vez por emenda;
- o município é o do beneficiário, por nome em maiúsculas e sem acento ("BRACO DO NORTE");
- o CSV de emendas vem em UTF-8 com BOM; o razão financeiro, em latin-1; ambos com `;` e
  vírgula decimal;
- "Valor Repassado" vazio quando ainda não há transferência; a soma dos pagamentos do razão
  difere do repassado em ~7% das transferências (devoluções e estornos), por isso o pago é o
  repassado que o próprio sistema mostra;
- autores coletivos ("BANCADA DO OESTE") e nome com apelido entre parênteses
  ("MARCOS JOSÉ ABREU ( MARQUITO)").

Recorte: só as emendas executadas por transferência voluntária no SC Transferências
(entidades sem fins lucrativos, APAEs, consórcios). Repasses fundo a fundo da saúde e
transferências especiais a prefeituras não passam por esse sistema e ficam de fora.
"""

import csv
import io
import re
import sys
import time
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FonteIngestao
from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "sctransferencias_emendas"
UF = "SC"
URL = "https://sctransf-api.prod.okd4.ciasc.sc.gov.br/csv/emendas"
URL_FINANCEIRO = (
    "https://arquivos.transparencia.sc.gov.br/sctransferencias/dados-abertos/"
    "dados_financeiros_{ano}.zip"
)
PAGINA = "https://consultas.sctransferencias.cge.sc.gov.br/pesquisa-detalhada/emendas"
PRIMEIRO_ANO = 2022  # primeiro ano com emendas no sistema
PAUSA = 1.0
MINIMO = 500  # menos linhas que isso é falha da fonte (eram 2.490 em 19/10/2026)
ARQUIVO_EMENDAS = "emendas.csv"
FONTE_NOME = "Emendas impositivas no SC Transferências (Controladoria-Geral do Estado de SC)"
CASA = "Assembleia Legislativa de Santa Catarina (ALESC)"
# Propostas que não vão adiante: o previsto delas não entra.
SITUACOES_FORA = ("Cancelada", "Desfavorável", "Não Homologado")
RECORTE = (
    "Só as emendas executadas por convênio ou termo de fomento no SC Transferências, quase "
    "todas para entidades sem fins lucrativos (hospitais, APAEs, clubes, associações). "
    "Repasses da saúde fundo a fundo e transferências diretas às prefeituras não passam por "
    "esse sistema e ficam de fora. O município é o do beneficiário."
)
TERMOS = (
    "Previsto: valor da emenda na Lei Orçamentária (emenda impositiva), contado uma vez. "
    "Empenhado: reservado no orçamento para o convênio. Pago: repassado pelo Estado."
)

CNPJ = re.compile(r"^(?P<nome>.*?)\s*\((?P<doc>\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\)\s*$")
CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")


def _valor(texto: str | None) -> Decimal | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    return Decimal(texto.replace(".", "").replace(",", ".") if "," in texto else texto)


def _texto(texto: str | None) -> str | None:
    texto = " ".join((texto or "").split())
    return texto or None


def favorecido(texto: str) -> tuple[str | None, str | None]:
    """'NOME (82.804.642/0001-08)' -> (nome, cnpj só com dígitos). Pessoa física (CPF): sem
    nome nem documento (coleta mínima)."""
    achado = CNPJ.match(texto or "")
    if achado:
        return _texto(achado["nome"]), re.sub(r"\D", "", achado["doc"])
    if CPF.search(texto or ""):
        return None, None
    return _texto(texto), None


nomes_do_autor = base.nomes_do_autor


def ler_emendas(conteudo: bytes) -> list[dict[str, Any]]:
    """CSV de emendas do SC Transferências -> uma linha por proposta."""
    texto = conteudo.decode("utf-8-sig")
    linhas = []
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        autor = _texto(x["Deputado"]) or ""
        nome, cnpj = favorecido(x["Beneficiário"])
        natureza = _texto(x["Natureza Jurídica Proponente"])
        if nome is None and cnpj is None:
            natureza = "Pessoa física"
        linhas.append(
            {
                "uf": UF,
                "ano": int(x["Ano"]),
                "codigo": x["Nº Emenda"].strip(),
                "proposta": x["Nº Proposta"].strip(),
                "transferencia": _texto(x["Nº Transferência"]),
                "tipo": "bancada"
                if comum.chave_nome(autor).startswith("BANCADA")
                else "individual",
                "autor_nome": autor,
                "autor_chave": comum.chave_nome(autor),
                "municipio_nome": _texto(x["Município"]) or "",
                "favorecido_nome": nome,
                "favorecido_cnpj": cnpj,
                "favorecido_natureza": natureza,
                "orgao": _texto(re.sub(r"\s*\(\d+\)\s*$", "", x["Concedente"] or "")),
                "instrumento": _texto(x["Instrumento"]),
                "objeto": _texto(x["Objeto Emenda"]),
                "situacao_proposta": _texto(x["Situação Proposta"]),
                "situacao_transferencia": _texto(x["Situação Transferência"]),
                # O valor atualizado (remanejamentos) é o que vale; difere em ~11 de 2.490.
                "valor_previsto": _valor(x["Valor Atualizado"]) or _valor(x["Valor Emenda"]) or 0,
                "valor_pago": _valor(x["Valor Repassado"]) or Decimal(0),
            }
        )
    return linhas


def empenhado_por_transferencia(financeiros: list[bytes]) -> dict[str, Decimal]:
    """Soma do valor empenhado (já líquido de anulações) por transferência, em todos os anos
    do razão financeiro. Lido em fluxo (cada CSV tem ~15 mil linhas)."""
    soma: dict[str, Decimal] = {}
    for conteudo in financeiros:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for nome in z.namelist():
                if not nome.lower().endswith(".csv"):
                    continue
                with z.open(nome) as arquivo:
                    texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
                    for x in csv.DictReader(texto, delimiter=";"):
                        valor = _valor(x.get("vlempenho"))
                        tr = (x.get("nutransferencia") or "").strip()
                        if tr and valor:
                            soma[tr] = soma.get(tr, Decimal(0)) + valor
    return soma


def empacotar(emendas: bytes, financeiros: dict[int, bytes]) -> bytes:
    """O CSV de emendas e os razões financeiros num zip só (bruto da carga)."""
    arquivos = {f"dados_financeiros_{ano}.zip": c for ano, c in financeiros.items()}
    return base.empacotar({ARQUIVO_EMENDAS: emendas, **arquivos})


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    """Bruto (zip com emendas.csv e os dados_financeiros_AAAA.zip) -> linhas da tabela."""
    with zipfile.ZipFile(io.BytesIO(pacote)) as z:
        linhas = ler_emendas(z.read(ARQUIVO_EMENDAS))
        financeiros = [z.read(n) for n in z.namelist() if n.startswith("dados_financeiros_")]
    empenhado = empenhado_por_transferencia(financeiros)
    for linha in linhas:
        tr = linha["transferencia"]
        linha["valor_empenhado"] = empenhado.get(tr) if tr else None
    return linhas


def carregar(session: Session, pacote: bytes, ingestao: FonteIngestao) -> int:
    return base.gravar(session, sys.modules[__name__], normalizar(pacote), ingestao)


def baixar(client: httpx.Client, hoje: date | None = None) -> bytes:
    hoje = hoje or date.today()
    emendas = comum.get_bytes(client, URL)
    financeiros = {}
    for ano in range(PRIMEIRO_ANO, hoje.year + 1):
        time.sleep(PAUSA)
        financeiros[ano] = comum.get_bytes(client, URL_FINANCEIRO.format(ano=ano))
    return empacotar(emendas, financeiros)


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
