"""Emendas de deputados estaduais de Minas Gerais (SEGOV/MG, Portal de Emendas Estaduais).

Fonte: o conjunto "Emendas Parlamentares Estaduais" do portal de dados abertos de MG
(dados.mg.gov.br/dataset/portal_emendas_estaduais, Secretaria de Estado de Governo), arquivo
"Emendas Estaduais - Indicações" (`vw_sg_v2_ep_indic_recursos_tw.csv`, ~30 MB): uma linha por
**indicação** de recurso de emenda impositiva (2023 em diante), com o deputado (ou bloco ou
bancada) responsável, município (código IBGE), beneficiário (nome, CNPJ e tipo), ação, valor
indicado, empenhado, liquidado e pago (acumulados, inclusive restos a pagar), situação da
indicação e do instrumento. Atualização semanal pela SEGOV. Sem login nem captcha.

Armadilhas (amostra de 21/10/2026, 37.200 indicações):
- números exportados como decimal: código IBGE "3147006,0" e CNPJ "18278051000145,0"; CNPJ
  que começa com zero perdeu o zero ("1234567000189,0", 13 dígitos): completa-se à esquerda;
- UTF-8 com BOM, `;` e vírgula decimal;
- 3.600 indicações a caixas escolares vêm sem código IBGE (só o nome do município);
- autores coletivos: "BLOCO ..." (6.030 linhas) e "BANCADA ..." (337);
- indicações reprovadas pelo órgão (2.943) ficam no arquivo com valores zerados ou
  parciais: o valor indicado delas não entra no previsto;
- `valor_pago_ano` é só o pago no ano; o que vale é `valor_pago` (acumulado).
"""

import csv
import io
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from ingestion import comum
from ingestion.emendas_estaduais import base

FONTE = "segov_mg_emendas"
UF = "MG"
URL = (
    "https://dados.mg.gov.br/dataset/715a1617-078b-4c07-8657-fe16894b62c2/resource/"
    "d85d9a92-dd8e-473d-bcb4-a4f3d13309b1/download/vw_sg_v2_ep_indic_recursos_tw.csv"
)
PAGINA = "https://dados.mg.gov.br/dataset/portal_emendas_estaduais"
FONTE_NOME = "Portal de Emendas Estaduais (Secretaria de Estado de Governo de MG)"
CASA = "Assembleia Legislativa de Minas Gerais (ALMG)"
MINIMO = 10_000  # eram 37.200 indicações em 21/10/2026
ARQUIVO = "indicacoes.csv"
SITUACOES_FORA = ("REPROVADO",)
RECORTE = (
    "Emendas impositivas de deputados estaduais, blocos e bancadas indicadas desde 2023, "
    "uma linha por indicação de recurso (prefeitura, fundo de saúde, entidade, caixa "
    "escolar ou órgão do Estado). Indicações reprovadas pelo órgão ficam fora do previsto. "
    "O município é o da indicação."
)
TERMOS = (
    "Previsto: valor indicado pelo deputado. Empenhado: reservado no orçamento. Pago: "
    "repassado ou pago pelo Estado, somando o que ficou para o ano seguinte (restos a pagar)."
)


def _numero(x: str | None) -> str:
    """'3147006,0' -> '3147006' (número exportado como decimal)."""
    return re.sub(r"[.,]0+$", "", (x or "").strip())


def _cnpj(x: str | None) -> str | None:
    d = base.so_digitos(_numero(x))
    return d.zfill(14) if 12 <= len(d) <= 14 else None


def ler(conteudo: bytes) -> list[dict[str, Any]]:
    linhas = []
    texto = conteudo.decode("utf-8-sig")
    for x in csv.DictReader(io.StringIO(texto, newline=""), delimiter=";"):
        autor = base.texto(x["responsavel"]) or ""
        classe = comum.chave_nome(x["classificacao_resp_descricao"])
        numero = _numero(x["numero_indicacao"])
        linhas.append(
            {
                "ano": int(_numero(x["ano_exercicio"])),
                "codigo": numero,
                "proposta": numero,
                "transferencia": base.texto(x["instrumento_numero"]),
                "tipo": "individual" if classe == "PARLAMENTAR ESTADUAL" else "bancada",
                "autor_nome": autor,
                "municipio_nome": base.texto(x["municipio"]) or "",
                "municipio_ibge": _numero(x["municipio_ibge"]) or None,
                "favorecido_nome": base.texto(x["beneficiario_nome"]),
                "favorecido_cnpj": _cnpj(x["beneficiario_cnpj"]),
                "favorecido_natureza": base.texto(x["beneficiario_tipo"]),
                "orgao": base.texto(x["uo_descricao"]),
                "instrumento": base.texto(x["tipo_indicacao"]),
                "objeto": base.sem_cpf(
                    base.texto(x["descricao_indicacao"]) or base.texto(x["acao_nome"])
                ),
                "situacao_proposta": base.texto(x["status_indicacao"]),
                "situacao_transferencia": base.texto(x["status_transparencia_descricao"]),
                "valor_previsto": base.valor(x["valor_indicacao"]) or Decimal(0),
                "valor_empenhado": base.valor(x["valor_empenhado"]),
                "valor_pago": base.valor(x["valor_pago"]) or Decimal(0),
            }
        )
    return linhas


def normalizar(pacote: bytes) -> list[dict[str, Any]]:
    return ler(base.desempacotar(pacote)[ARQUIVO])


def baixar(client: httpx.Client) -> bytes:
    return base.empacotar({ARQUIVO: comum.get_bytes(client, URL)})


def executar(de_raw: Path | None = None) -> int:
    return base.executar(sys.modules[__name__], de_raw=de_raw)


if __name__ == "__main__":
    base.main(sys.modules[__name__])
