"""Emendas de deputados estaduais de Pernambuco (SEPLAG/PE, painéis de emendas).

Fonte: o conjunto "Emendas Parlamentares Estaduais" do portal de dados abertos de PE
(dados.pe.gov.br/dataset/emendasparlamentaresestaduais, SEPLAG), as três "Tabela Completa"
do ano corrente, uma por forma de execução: GTV (transferência voluntária a entidades e
fundo a fundo), DIRETA (execução pelo próprio Estado) e PIX (transferência especial às
prefeituras). Uma linha por emenda × empenho, com autor, número da emenda na ALEPE,
município, beneficiário, objeto, situação e empenhado, liquidado e pago; o orçamento atual
da emenda (depois dos ciclos de remanejamento) se repete nas linhas da mesma emenda. Os
endereços mudam a cada publicação: são lidos pela API do CKAN. Sem login nem captcha.

Os arquivos de 2012 a 2025 do mesmo conjunto são empenhos sem autor nem município (o autor
só aparece no texto livre do histórico): ficam de fora (ver docs/DECISOES.md).

Armadilhas (amostra de 21/10/2026):
- registros terminam em CRLF, mas o objeto de uma emenda PIX tem quebras LF soltas, sem
  aspas: lido como CSV comum, corta a linha e cria uma "linha" lixo. O registro é separado
  pelo CRLF e o LF de dentro vira espaço; campos com `;` vêm entre aspas;
- a mesma emenda × empenho aparece uma vez por chamamento público ligado a ela (só a coluna
  `nu_chamamento` muda; 8 pares na tabela GTV de 21/10/2026): os valores são do empenho e
  entram uma vez;
- na execução DIRETA o credor é o fornecedor (ex.: loja de equipamentos), não quem recebe;
- números com ponto decimal ("100000.0"); UTF-8 com BOM e `;`;
- emenda remanejada para outra fica com orçamento atual zero.
"""

import csv
import re
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "seplag_pe_emendas"
UF = "PE"
CKAN = "https://dados.pe.gov.br/api/3/action/package_show"
CONJUNTO = "emendasparlamentaresestaduais"
URL = f"{CKAN}?id={CONJUNTO}"
PAGINA = f"https://dados.pe.gov.br/dataset/{CONJUNTO}"
FONTE_NOME = "Emendas Parlamentares Estaduais (Secretaria de Planejamento de PE)"
CASA = "Assembleia Legislativa de Pernambuco (ALEPE)"
MINIMO = 800  # eram 2.364 linhas em 21/10/2026
PAUSA = 1.0
SITUACOES_FORA: tuple[str, ...] = ()
VERSAO = 2  # 21/10/2026: linhas repetidas pela exportação entram uma vez
MODALIDADES = {"gtv": "Transferência voluntária", "direta": "Execução direta", "pix": "PIX"}
SIGLA = {"gtv": "G", "direta": "D", "pix": "P"}
VALORES = (
    "valor_empenhado",
    "valor_liquidado",
    "valor_pago",
    "valor_rp_pago",
    "orcamento_atual",
)  # chave curta: "G1078:2026NE000617"
ARQUIVO = re.compile(r"^tabela_completa_(gtv|direta|pix)\.csv$", re.I)
RECORTE = (
    "Emendas impositivas de deputados estaduais da Lei Orçamentária do ano corrente, nas "
    "três formas de execução (transferência a entidades e fundos, execução pelo próprio "
    "Estado e transferência especial às prefeituras). Anos anteriores ficam de fora: os "
    "arquivos antigos não trazem autor nem município. Na execução pelo Estado, quem aparece "
    "como favorecido é o fornecedor."
)
TERMOS = (
    "Previsto: orçamento atual da emenda (depois dos remanejamentos), contado uma vez. "
    "Empenhado: reservado no orçamento. Pago: pago pelo Estado."
)


def registros(texto: str) -> list[list[str]]:
    """Linhas do CSV. Cada registro termina em CRLF; dentro do objeto pode haver LF solto
    (sem aspas), que vira espaço. Campos com `;` vêm entre aspas."""
    fisicas = texto.split("\r\n") if "\r\n" in texto else texto.split("\n")
    juntas = [linha.replace("\n", " ") for linha in fisicas if linha.strip()]
    return list(csv.reader(juntas, delimiter=";"))


def ler(conteudo: bytes, modalidade: str) -> list[dict[str, Any]]:
    linhas_brutas = registros(conteudo.decode("utf-8-sig"))
    cabecalho, corpo = linhas_brutas[0], linhas_brutas[1:]
    # (emenda, empenho) -> valores: a exportação repete o empenho uma vez por chamamento
    # público ligado à emenda (só `nu_chamamento` muda); os valores são do empenho e entram
    # uma vez.
    vistos: dict[str, tuple[str, ...]] = {}
    repeticoes: dict[str, int] = {}
    linhas = []
    for valores in corpo:
        if len(valores) != len(cabecalho):
            raise ValueError(f"{FONTE}: linha com {len(valores)} campos: {valores[:6]}")
        x = dict(zip(cabecalho, valores, strict=True))
        codigo = (x.get("codigo_alepe") or "").strip()
        empenho = (x.get("numero_empenho") or "").strip()
        chave = f"{SIGLA[modalidade]}{codigo}:{empenho or '-'}"
        financeiro = tuple(x.get(c) or "" for c in VALORES)
        if vistos.get(chave) == financeiro:  # repetição do mesmo empenho
            continue
        vistos.setdefault(chave, financeiro)
        repeticoes[chave] = repeticoes.get(chave, 0) + 1
        if repeticoes[chave] > 1:
            chave = f"{chave}:{repeticoes[chave]}"
        doc, _, nome = (x.get("nome_credor") or "").partition(" - ")
        doc = base.so_digitos(doc)
        nome = base.texto(nome)
        natureza = base.texto(x.get("beneficiario"))
        if len(doc) == 11:  # pessoa física: sem nome nem CPF (coleta mínima)
            nome, natureza = None, "Pessoa física"
        pago = (base.valor(x.get("valor_pago")) or Decimal(0)) + (
            base.valor(x.get("valor_rp_pago")) or Decimal(0)
        )
        linhas.append(
            {
                "ano": int(x["ano"]),
                "codigo": codigo,
                "proposta": chave,
                "transferencia": empenho or None,
                "tipo": None,
                "autor_nome": base.texto(x.get("autor")) or "",
                "municipio_nome": base.texto(x.get("municipio")) or "",
                "municipio_ibge": None,
                "favorecido_nome": nome,
                "favorecido_cnpj": base.cnpj(doc),
                "favorecido_natureza": natureza,
                "orgao": base.texto(x.get("nome_ug")),
                "instrumento": MODALIDADES[modalidade],
                "objeto": base.sem_cpf(base.texto(x.get("objeto"))),
                "situacao_proposta": base.texto(x.get("classificacao_emenda")),
                "situacao_transferencia": base.texto(x.get("status_resolucao_tce")),
                "valor_previsto": base.valor(x.get("orcamento_atual")) or Decimal(0),
                "valor_empenhado": base.valor(x.get("valor_empenhado")),
                "valor_pago": pago,
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    linhas = []
    for nome, conteudo in sorted(base.desempacotar(pacote).items()):
        achado = ARQUIVO.match(nome)
        if achado:
            linhas += ler(conteudo, achado.group(1).lower())
    return linhas


def arquivos(pacote_ckan: dict) -> dict[str, str]:
    """Resposta do package_show -> {nome do arquivo: URL} das três tabelas completas."""
    saida = {}
    for r in pacote_ckan["result"]["resources"]:
        nome = (r.get("url") or "").rsplit("/", 1)[-1]
        if ARQUIVO.match(nome):
            saida[nome.lower()] = r["url"]
    return saida


def baixar(client: httpx.Client) -> bytes:
    urls = arquivos(comum.get_json(client, CKAN, params={"id": CONJUNTO}))
    if len(urls) != len(MODALIDADES):
        raise ValueError(f"{FONTE}: esperava 3 tabelas completas, achei {sorted(urls)}.")
    saida = {}
    for nome, url in sorted(urls.items()):
        time.sleep(PAUSA)
        saida[nome] = comum.get_bytes(client, url)
    return base.empacotar(saida)


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
