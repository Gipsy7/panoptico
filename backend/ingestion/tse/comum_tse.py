"""Leitura dos arquivos do TSE (zip com um CSV por UF, separados por ';', em latin-1)."""

import csv
import io
import zipfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
NULOS = {"", "#NULO", "#NULO#", "#NE", "-1", "-3", "-4"}


def abrir_zip(payload: bytes | Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(payload) if isinstance(payload, bytes) else payload)


def linhas(payload: bytes | Path, prefixo: str) -> Iterator[dict[str, str]]:
    """Linhas dos CSVs por UF cujo nome começa com o prefixo. O arquivo "_BRASIL" junta
    todos os outros e fica de fora para não contar duas vezes."""
    with abrir_zip(payload) as z:
        for nome in sorted(z.namelist()):
            base = nome.rsplit("/", 1)[-1]
            if not base.startswith(prefixo) or not base.endswith(".csv") or "_BRASIL" in base:
                continue
            with z.open(nome) as bruto:
                texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
                yield from csv.DictReader(texto, delimiter=";")


def texto(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return None if valor in NULOS else valor


def valor(texto_valor: str | None) -> Decimal:
    """'750000,00' -> Decimal('750000.00')."""
    limpo = (texto_valor or "0").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except ArithmeticError:
        return Decimal(0)


def cpf(valor_cpf: str | None) -> str | None:
    digitos = "".join(c for c in (valor_cpf or "") if c.isdigit())
    return digitos.zfill(11) if len(digitos) >= 9 else None
