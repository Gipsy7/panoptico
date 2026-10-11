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
