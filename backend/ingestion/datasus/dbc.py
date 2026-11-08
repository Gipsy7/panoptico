"""Arquivos DBC do DATASUS (FTP público): DBF comprimido com o "implode" da PKWARE.

Descomprimimos com `pyreaddbc` e lemos o DBF de largura fixa direto, só as colunas pedidas, em
fluxo (o de SP passa de 200 MB aberto)."""

import re
import shutil
import struct
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

FTP = "ftp://ftp.datasus.gov.br/dissemin/publicos/"


def registros(dbf: Path, colunas: tuple[str, ...]) -> Iterator[dict[str, str]]:
    """Cada registro não apagado do DBF, só com as colunas pedidas (texto sem espaços)."""
    with dbf.open("rb") as f:
        n, tam_cab, tam_reg = struct.unpack("<IHH", f.read(32)[4:12])
        campos: dict[str, tuple[int, int]] = {}
        pos = 1  # o 1º byte do registro é a marca de apagado
        while True:
            d = f.read(32)
            if not d or d[0] == 0x0D:
                break
            campos[d[:11].split(b"\0")[0].decode("latin-1")] = (pos, d[16])
            pos += d[16]
        faixas = [(c, *campos[c]) for c in colunas]
        f.seek(tam_cab)
        for _ in range(n):
            r = f.read(tam_reg)
            if len(r) < tam_reg:
                break
            if r[0:1] == b"*":
                continue
            yield {c: r[p : p + t].decode("latin-1").strip() for c, p, t in faixas}


def abrir(url: str, tentativas: int = 5):
    for t in range(tentativas):
        try:
            return urllib.request.urlopen(url, timeout=120)  # noqa: S310 (FTP público do DATASUS)
        except OSError:
            if t == tentativas - 1:
                raise
            time.sleep(10 * (t + 1))
    raise RuntimeError("inalcançável")


def listar(pasta: str, padrao: re.Pattern) -> list[re.Match]:
    """Os nomes de arquivo da pasta do FTP que casam com o padrão."""
    with abrir(FTP + pasta) as r:
        texto = r.read().decode("latin-1")
    nomes = (linha.split()[-1] for linha in texto.splitlines() if linha.split())
    return [m for m in map(padrao.match, nomes) if m]


def ler_remoto(pasta: str, nome: str, colunas: tuple[str, ...]) -> Iterator[dict[str, str]]:
    """Baixa um DBC do FTP para uma pasta temporária, abre e devolve os registros."""
    import pyreaddbc  # só na carga: a API não precisa dele

    tmp = Path(tempfile.mkdtemp(prefix="dbc_"))
    try:
        dbc, dbf = tmp / nome, tmp / (nome[:-4] + ".dbf")
        with abrir(FTP + pasta + nome) as r, dbc.open("wb") as saida:
            shutil.copyfileobj(r, saida, 1 << 20)
        pyreaddbc.dbc2dbf(str(dbc), str(dbf))
        dbc.unlink()
        yield from registros(dbf, colunas)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
