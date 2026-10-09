"""Normalizadores comuns às fontes de Justiça e controle."""

import re

# Segmentos do Judiciário no número único (dígito J), Resolução CNJ 65/2008.
SEGMENTOS = {
    "1": "STF",
    "2": "CNJ",
    "3": "STJ",
    "4": "Justiça Federal",
    "5": "Justiça do Trabalho",
    "6": "Justiça Eleitoral",
    "7": "Justiça Militar da União",
    "8": "Justiça Estadual",
    "9": "Justiça Militar Estadual",
}


def numero_cnj(valor: str | None) -> str | None:
    """'06000934620246170112' -> '0600093-46.2024.6.17.0112' (NNNNNNN-DD.AAAA.J.TR.OOOO).

    Confere o dígito verificador (módulo 97): número com dígito errado vira None, para não
    publicar um processo que não existe."""
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) != 20:
        return None
    n, dd, ano, j, tr, origem = (
        digitos[:7], digitos[7:9], digitos[9:13], digitos[13], digitos[14:16], digitos[16:]
    )  # fmt: skip
    if 98 - int(n + ano + j + tr + origem + "00") % 97 != int(dd):
        return None
    return f"{n}-{dd}.{ano}.{j}.{tr}.{origem}"
