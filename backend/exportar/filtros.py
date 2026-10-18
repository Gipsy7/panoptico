"""Defesa em profundidade contra dado pessoal que a consulta não tenha barrado."""

import re

# CPF formatado (000.000.000-00): nunca sai, em coluna nenhuma.
CPF_FORMATADO = re.compile(
    r"(?<![\d*])(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\*{3}\.\d{3}\.\d{3}-\*{2})(?![\d*])"
)
# Sequência de exatamente 11 dígitos: só em colunas de texto livre (nomes de MEI trazem o CPF
# no fim, "FULANO 12345678901"; ids e números de processo ficam de fora desta regra).
ONZE_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")

OMITIDO = "[CPF omitido]"


def limpar(valor: str, livre: bool = False) -> str:
    valor = CPF_FORMATADO.sub(OMITIDO, valor)
    if livre:
        valor = ONZE_DIGITOS.sub(OMITIDO, valor)
    return valor
