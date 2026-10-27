"""Leitura dos arquivos do TSE (zip com um CSV por UF, separados por ';', em latin-1)."""

import csv
import io
import zipfile
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
NULOS = {"", "#NULO", "#NULO#", "#NE", "-1", "-3", "-4"}
# Em 2002 e 2006 o SQ_CANDIDATO é um número sequencial por UF e se repete
# entre estados; nesses anos a chave da candidatura é "<SG_UF>-<SQ>".
SQ_POR_UNIDADE = {2002, 2006}


def abrir_zip(payload: bytes | Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(payload) if isinstance(payload, bytes) else payload)


def linhas(
    payload: bytes | Path, prefixo: str, so_brasil: bool = False
) -> Iterator[dict[str, str]]:
    """Linhas dos CSVs por UF cujo nome começa com o prefixo. O arquivo "_BRASIL" junta
    todos os outros e fica de fora para não contar duas vezes (`so_brasil` lê só ele)."""
    with abrir_zip(payload) as z:
        for nome in sorted(z.namelist()):
            base = nome.rsplit("/", 1)[-1]
            if not base.startswith(prefixo) or not base.endswith(".csv"):
                continue
            if ("_BRASIL" in base) != so_brasil:
                continue
            with z.open(nome) as bruto:
                texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
                yield from csv.DictReader(texto, delimiter=";")


def uf_da_disputa(linha: dict[str, str]) -> str:
    """UF da disputa. Em 2006 as linhas de presidente do arquivo de votação trazem em SG_UF o
    estado da zona e só em SG_UE o "BR" da disputa nacional; nos demais casos SG_UE é o
    município (2002) ou igual à UF."""
    return "BR" if linha.get("SG_UE", "").strip() == "BR" else linha["SG_UF"].strip()


def sq_candidato(linha: dict[str, str]) -> str:
    """Chave da candidatura no ano (igual nos arquivos de candidaturas e de votação)."""
    sq = linha["SQ_CANDIDATO"].strip()
    if int(linha.get("ANO_ELEICAO") or 0) in SQ_POR_UNIDADE:
        return f"{uf_da_disputa(linha)}-{sq}"
    return sq


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


def titulo(valor_titulo: str | None) -> str | None:
    digitos = "".join(c for c in (valor_titulo or "") if c.isdigit())
    return digitos.zfill(12) if len(digitos) >= 8 else None


def data(valor_data: str | None) -> date | None:
    """'21/02/1959' -> date(1959, 2, 21)."""
    try:
        dia, mes, ano = (valor_data or "").strip().split("/")
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
