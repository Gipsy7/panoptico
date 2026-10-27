"""Emendas de deputados distritais do DF (Portal da Transparência do Distrito Federal).

Fonte: a consulta "Emendas Parlamentares Distritais" do Portal da Transparência do DF
(transparencia.df.gov.br/#/despesas/emendas-parlamentares) lê uma API pública
(`/api/despesa/emendas-parlamentares?anoExercicio=AAAA&page=N&size=100`; os anos em
`/api/despesa/emendas-parlamentares/anos`), uma linha por autor × programa de trabalho ×
natureza × fonte × unidade gestora: autor, tipo da emenda, órgão, programa de trabalho (com o
subtítulo, que traz a região administrativa), dotação aprovada, autorizada, empenhado,
liquidado e pago. Sem login nem captcha.

Armadilhas (amostra de 27/10/2026, 2016 a 2026):
- a paginação não tem ordem estável: percorrida página a página, a consulta de 2025 devolve
  linhas repetidas e nunca mostra 27 das 656 (o mesmo em seis passadas; `sort` dá erro 500).
  Por isso cada ano é lido primeiro inteiro e, se faltar linha, de novo filtrado por autor
  (`nomeAutor`, que casa por "contém" e cabe numa página), até completar o total do ano; no
  fim, a contagem e as somas de autorizado, empenhado e pago têm de bater com o `totalizador`
  que a própria API devolve, ou a carga aborta;
- de 2016 a 2020 o empenhado e o liquidado vêm zerados com pago preenchido (R$ 85 mi pagos
  em 2016 sem nada empenhado): ficam de fora; carregamos de 2021 em diante;
- a API exige o cabeçalho `x-client-id`, um identificador de sessão que a própria página
  sorteia (UUID aleatório, sem cadastro); mandamos um novo a cada carga, como a página;
- o servidor responde 406 a `Accept: application/json` na página inicial, mas a API aceita;
- não há número da emenda nem identificador da linha: a chave é o ano com um resumo (sha1)
  dos códigos da linha (autor, unidade gestora, gestão, programa de trabalho, natureza,
  fonte, esfera e unidade orçamentária), conferido como único em todos os anos;
- emendas de vários autores vêm num texto só ("CHICO VIGILANTE - HERMETO - ..."): ficam como
  coletivas, sem pessoa; o mesmo nome repetido com e sem acento ("FÁBIO FELIX - FÁBIO FÉLIX")
  vira um autor só, mas grafias diferentes da mesma pessoa ("ARLETE AVELAR SAMPAIO - ARLETE
  SAMPAIO") ficam coletivas (não ligamos por aproximação);
- não há favorecido nem município: o DF é um município só no IBGE (Brasília), e a região
  administrativa só aparece no nome do subtítulo;
- textos com espaços sobrando no fim ("DIREITOS HUMANOS          ").
"""

import hashlib
import json
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "transparencia_df_emendas"
UF = "DF"
API = "https://www.transparencia.df.gov.br/api/despesa/emendas-parlamentares"
URL = f"{API}?anoExercicio={{ano}}"
PAGINA = "https://www.transparencia.df.gov.br/#/despesas/emendas-parlamentares"
FONTE_NOME = "Emendas Parlamentares Distritais (Portal da Transparência do Distrito Federal)"
CASA = "Câmara Legislativa do Distrito Federal (CLDF)"
PRIMEIRO_ANO = 2021  # antes, empenhado zerado com pago preenchido (ver armadilhas)
MINIMO = 2000  # eram 4.215 linhas de 2021 a 2026 em 27/10/2026
POR_PAGINA = 100
POR_AUTOR = 150  # cabe numa página só (o maior autor num ano tinha ~50 linhas)
VALORES = ("valorDespesaAutorizadaEmendas", "valorEmpenhadoEmendas", "valorEmpenhoPago")
PAUSA = 0.5
ARQUIVO = "emendas.json"
SITUACOES_FORA: tuple[str, ...] = ()
BRASILIA = "5300108"
SEPARADOR_AUTORES = " - "
RECORTE = (
    "Emendas de deputados distritais desde 2021, uma linha por autor e programa de trabalho "
    "(com natureza e fonte da despesa), como o Portal da Transparência do DF publica. A fonte "
    "não informa quem recebeu. Para o IBGE o Distrito Federal é um município só (Brasília); a "
    "região administrativa aparece no nome da ação. Emendas de vários deputados juntos ficam "
    "como coletivas."
)
TERMOS = (
    "Previsto: valor autorizado da emenda (aprovado na lei, com alterações e bloqueios). "
    "Empenhado: reservado no orçamento. Pago: o que o portal mostra como pago no ano."
)


def chave(x: dict[str, Any]) -> str:
    """Ano com um resumo dos códigos que identificam a linha na consulta."""
    partes = [
        base.texto(x.get("nomeAutor")) or "",
        x.get("codigoUnidadeGestora"),
        x.get("codigoGestao"),
        (base.texto(x.get("nomeProgramaTrabalho")) or "").split(" ")[0],
        x.get("codigoGrupoNatureza"),
        x.get("codigoFonte"),
        x.get("codigoEsfera"),
        x.get("codigoUnidadeOrcamentaria"),
    ]
    resumo = hashlib.sha1(json.dumps(partes, ensure_ascii=False).encode()).hexdigest()[:16]
    return f"{int(x['anoExercicio'])}:{resumo}"


def ler(linhas_json: list[dict[str, Any]]) -> list[dict[str, Any]]:
    linhas = []
    for x in linhas_json:
        autor = base.texto(x.get("nomeAutor")) or ""
        partes = autor.split(SEPARADOR_AUTORES)
        # "FÁBIO FELIX - FÁBIO FÉLIX": o mesmo nome escrito duas vezes é um autor só.
        if len(partes) > 1 and len({comum.chave_nome(n) for n in partes}) == 1:
            autor, partes = partes[0], partes[:1]
        coletiva = len(partes) > 1
        id_linha = chave(x)
        linhas.append(
            {
                "ano": int(x["anoExercicio"]),
                "codigo": id_linha,
                "proposta": id_linha,
                "transferencia": None,
                "tipo": "bancada" if coletiva else None,
                "autor_nome": autor,
                "municipio_nome": "Brasília",
                "municipio_ibge": BRASILIA,
                "favorecido_nome": None,
                "favorecido_cnpj": None,
                "favorecido_natureza": base.texto(x.get("nomeModalidade")),
                "orgao": base.texto(x.get("nomeUnidadeGestora")),
                "instrumento": base.texto(x.get("nomeElemento")),
                "objeto": base.sem_cpf(base.texto(x.get("nomeProgramaTrabalho"))),
                "situacao_proposta": base.texto(x.get("nomeTipoEmenda")),
                "situacao_transferencia": None,
                "valor_previsto": base.valor(x.get("valorDespesaAutorizadaEmendas")) or Decimal(0),
                "valor_empenhado": base.valor(x.get("valorEmpenhadoEmendas")),
                "valor_pago": base.valor(x.get("valorEmpenhoPago")) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    # parse_float=Decimal: os valores vêm como número no JSON e não podem passar por float.
    return ler(json.loads(base.desempacotar(pacote)[ARQUIVO], parse_float=Decimal))


def _pagina(client: httpx.Client, ano: int, pagina: int, tamanho: int, **filtro) -> dict:
    resposta = comum.get_json(
        client, API, params={"anoExercicio": ano, "page": pagina, "size": tamanho, **filtro}
    )
    time.sleep(PAUSA)
    return resposta


def conferir(ano: int, linhas: list[dict[str, Any]], total: int, totalizador: dict) -> None:
    """Contagem e somas iguais às que a própria API informa para o ano, ou aborta."""
    if len(linhas) != total:
        raise ValueError(f"{FONTE}: {len(linhas)} de {total} linhas de {ano}; abortando.")
    for campo in VALORES:
        soma = sum((Decimal(str(x[campo] or 0)) for x in linhas), Decimal(0))
        esperado = Decimal(str(totalizador.get(campo) or 0))
        if abs(soma - esperado) > Decimal("0.05"):
            raise ValueError(f"{FONTE}: {campo} de {ano} soma {soma}, a API diz {esperado}.")


def _ano(client: httpx.Client, ano: int, autores: list[str]) -> list[dict[str, Any]]:
    vistas: dict[str, dict[str, Any]] = {}
    pagina, total, totalizador = 0, None, {}
    while total is None or pagina * POR_PAGINA < total:
        resposta = _pagina(client, ano, pagina, POR_PAGINA)
        total, totalizador = int(resposta["totalElements"]), resposta["totalizador"] or {}
        if not resposta["content"]:
            break
        vistas.update((chave(x), x) for x in resposta["content"])
        pagina += 1
    for autor in autores:  # completa o que a paginação instável deixou de fora
        if len(vistas) >= total:
            break
        resposta = _pagina(client, ano, 0, POR_AUTOR, nomeAutor=autor)
        if int(resposta["totalElements"]) > POR_AUTOR:
            raise ValueError(f"{FONTE}: {autor} tem mais de {POR_AUTOR} linhas em {ano}.")
        vistas.update((chave(x), x) for x in resposta["content"])
    linhas = list(vistas.values())
    conferir(ano, linhas, total or 0, totalizador)
    return linhas


def baixar(client: httpx.Client) -> bytes:
    # Identificador de sessão que a página sorteia e manda em toda chamada à API.
    client.headers["x-client-id"] = str(uuid.uuid4())
    anos = [a for a in comum.get_json(client, f"{API}/anos") if int(a) >= PRIMEIRO_ANO]
    autores = [
        n for n in (base.texto(a.get("nome")) for a in comum.get_json(client, f"{API}/autor")) if n
    ]
    linhas: list[dict[str, Any]] = []
    for ano in sorted(anos):
        linhas += _ano(client, int(ano), autores)
    # Ordem fixa: o mesmo conteúdo dá o mesmo bruto (carga incremental por sha256).
    linhas.sort(key=chave)
    conteudo = json.dumps(linhas, ensure_ascii=False).encode()
    return base.empacotar({ARQUIVO: conteudo})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
