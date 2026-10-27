"""Emendas de deputados distritais do DF (Portal da Transparência do Distrito Federal).

Fonte: a consulta "Emendas Parlamentares Distritais" do Portal da Transparência do DF
(transparencia.df.gov.br/#/despesas/emendas-parlamentares) lê uma API pública
(`/api/despesa/emendas-parlamentares?anoExercicio=AAAA&page=N&size=100`; os anos em
`/api/despesa/emendas-parlamentares/anos`), uma linha por autor × programa de trabalho ×
natureza × fonte × unidade gestora: autor, tipo da emenda, órgão, programa de trabalho (com o
subtítulo, que traz a região administrativa), dotação aprovada, autorizada, empenhado,
liquidado e pago. Sem login nem captcha.

Armadilhas (amostra de 27/10/2026, 2016 a 2026):
- a API exige o cabeçalho `x-client-id`, um identificador de sessão que a própria página
  sorteia (UUID aleatório, sem cadastro); mandamos um novo a cada carga, como a página;
- o servidor responde 406 a `Accept: application/json` na página inicial, mas a API aceita;
- não há número da emenda nem identificador da linha: a chave é o ano com um resumo (sha1)
  dos códigos da linha (autor, unidade gestora, gestão, programa de trabalho, natureza,
  fonte, esfera e unidade orçamentária), conferido como único em todos os anos;
- emendas de vários autores vêm num texto só ("CHICO VIGILANTE - HERMETO - ..."): ficam como
  coletivas, sem pessoa;
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
MINIMO = 3000  # eram 6.0xx linhas de 2016 a 2026 em 27/10/2026
POR_PAGINA = 100
PAUSA = 0.5
ARQUIVO = "emendas.json"
SITUACOES_FORA: tuple[str, ...] = ()
BRASILIA = "5300108"
SEPARADOR_AUTORES = " - "
RECORTE = (
    "Emendas de deputados distritais desde 2016, uma linha por autor e programa de trabalho "
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
        coletiva = len(autor.split(SEPARADOR_AUTORES)) > 1
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


def baixar(client: httpx.Client) -> bytes:
    # Identificador de sessão que a página sorteia e manda em toda chamada à API.
    client.headers["x-client-id"] = str(uuid.uuid4())
    anos = comum.get_json(client, f"{API}/anos")
    linhas: list[dict[str, Any]] = []
    for ano in sorted(anos):
        pagina, total = 0, None
        do_ano: list[dict[str, Any]] = []
        while total is None or len(do_ano) < total:
            resposta = comum.get_json(
                client, API, params={"anoExercicio": ano, "page": pagina, "size": POR_PAGINA}
            )
            total = int(resposta["totalElements"])
            if not resposta["content"]:
                break
            do_ano += resposta["content"]
            pagina += 1
            time.sleep(PAUSA)
        if len(do_ano) != total:
            raise ValueError(f"{FONTE}: {len(do_ano)} de {total} linhas de {ano}; abortando.")
        linhas += do_ano
    conteudo = json.dumps(linhas, ensure_ascii=False).encode()
    return base.empacotar({ARQUIVO: conteudo})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
