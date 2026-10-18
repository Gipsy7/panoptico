"""Saneamento de texto vindo de fontes externas (nomes de fornecedores, órgãos)."""

import re

# surrogates soltos (não existem em UTF-8 válido e quebram o JSON) e caractere de substituição
_SUBSTITUICAO = re.compile(r"[\ud800-\udfff�]")
# caracteres de controle C0/C1 (os de espaço, como tab e nova linha, ficam para a normalização)
_CONTROLE = re.compile(r"[\x00-\x08\x0e-\x1b\x7f-\x9f]")


def _refazer_mojibake(texto: str) -> str:
    """UTF-8 lido como latin-1/cp1252 vira "Ã" ou "Â" mais outro caractere; só vale se o texto
    voltar a UTF-8 válido (texto normal, como "AÇÃO", não volta e fica como está)."""
    for codec in ("cp1252", "latin-1"):
        try:
            return texto.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return texto


def limpar_texto(texto: str | None) -> str | None:
    """Conserta o mojibake comum (UTF-8 lido como latin-1), tira surrogates soltos, caracteres de
    substituição e de controle, e normaliza os espaços. Texto sem problema volta igual."""
    if texto is None:
        return None
    texto = _SUBSTITUICAO.sub("", texto)
    if "Ã" in texto or "Â" in texto:
        texto = _refazer_mojibake(texto)
    texto = _CONTROLE.sub("", texto)
    return " ".join(texto.split())


# CPF solto no texto (11 dígitos, com ou sem pontuação; 12 quando a fonte digita um dígito a
# mais, como em "JOAO 014343640062") e CPF mascarado ("***.123.456-**"). Os limites de dígito
# impedem de morder um CNPJ (14 dígitos).
CPF = re.compile(
    r"(?<![\d*])(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2}\d?|\*{3}\.?\d{3}\.?\d{3}-?\*{2})(?![\d*])"
)


# CPF digitado errado (truncado, com espaço no lugar do traço, 9 a 10 dígitos soltos no fim do
# nome de MEI): na dúvida, número grande que não é CNPJ some do nome.
_ROTULO_CPF = re.compile(
    r"(?:(?<![A-Za-z])CPF\s*[:.]?\s*)?(?<![\d*])(?:"
    r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}\d?"  # 11 (ou 12) dígitos
    r"|\*{3}\.?\d{3}\.?\d{3}-?\*{2}"  # mascarado
    r"|\d{3}\.\d{3}\.\d{3}(?:[- ]?\d{1,2})?"  # pontuado e truncado
    r"|\d{9,10}(?: \d{2})?"  # 9 a 10 dígitos soltos
    r")(?![\d*])",
    re.IGNORECASE,
)


def sem_cpf(texto: str | None) -> str | None:
    """Tira CPF do texto, com o rótulo ("CPF:") e o traço que sobra na ponta. MEI traz o CPF
    dentro da razão social ('JOSE DA SILVA 12345678901'): regra fixa, CPF não vai para API,
    site nem exportação. Vazio vira None."""
    if not texto:
        return None
    limpo = " ".join(_ROTULO_CPF.sub(" ", limpar_texto(texto) or "").split())
    return limpo.strip(" -–—:;,/") or None
