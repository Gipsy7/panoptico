"""CNPJ numérico e alfanumérico (IN RFB 2229/2024, vigente desde julho de 2026).

O CNPJ alfanumérico tem 14 posições: as 12 primeiras (raiz + ordem) aceitam letras maiúsculas
e dígitos; as duas últimas (dígitos verificadores) são sempre números. O dígito verificador
usa o mesmo módulo 11 do CNPJ antigo, com o valor de cada caractere igual ao código ASCII
menos 48 (os dígitos continuam valendo 0 a 9; "A" vale 17). Por isso o algoritmo novo dá o
mesmo resultado nos CNPJs numéricos de sempre."""

import re

_SEPARADORES = re.compile(r"[.\-/\s]")
_FORMA = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")
_PESOS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)  # pesos das 13 posições do 2º dígito


def normalizar_cnpj(texto: str | None) -> str | None:
    """Tira pontos, traço e barra e põe em maiúsculas. None se não tem a forma de um CNPJ
    (14 posições, letras só nas 12 primeiras). Não confere os dígitos verificadores."""
    if not texto:
        return None
    limpo = _SEPARADORES.sub("", texto).upper()
    return limpo if _FORMA.match(limpo) else None


def _digito(base: str) -> int:
    pesos = _PESOS[-len(base) :]
    resto = sum((ord(c) - 48) * p for c, p in zip(base, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def digitos_verificadores(base12: str) -> str:
    """Os dois dígitos verificadores das 12 primeiras posições (letras maiúsculas ou números)."""
    d1 = _digito(base12)
    return f"{d1}{_digito(base12 + str(d1))}"


def cnpj_valido(texto: str | None) -> bool:
    """CNPJ (numérico ou alfanumérico) com forma e dígitos verificadores corretos.
    Sequências repetidas (00000000000000) não valem."""
    cnpj = normalizar_cnpj(texto)
    if cnpj is None or len(set(cnpj)) == 1:
        return False
    return cnpj[12:] == digitos_verificadores(cnpj[:12])
