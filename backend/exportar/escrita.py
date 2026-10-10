"""Escrita em fluxo: lê o banco em lotes e grava Parquet (zstd) e CSV.gz ao mesmo tempo."""

import csv
import gzip
import hashlib
import json
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import Connection, text

from exportar.conjuntos import Conjunto
from exportar.filtros import limpar

LOTE = 50_000

TIPO_ARROW = {
    "texto": pa.string(),
    "inteiro": pa.int64(),
    "decimal": pa.decimal128(20, 2),
    "data": pa.date32(),
    "datahora": pa.timestamp("us", tz="UTC"),
    "booleano": pa.bool_(),
    "json": pa.string(),
}


def _valor(v, tipo: str, livre: bool):
    if v is None:
        return None
    if tipo == "json":
        v = json.dumps(v, ensure_ascii=False, sort_keys=True)
    if isinstance(v, str):
        return limpar(v, livre)
    return v


def _celula_csv(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def exportar_conjunto(conn: Connection, conjunto: Conjunto, destino: Path) -> dict:
    """Grava `<nome>.parquet` e `<nome>.csv.gz` e devolve linhas, tamanhos e hashes."""
    colunas = conjunto.colunas
    schema = pa.schema([(c.nome, TIPO_ARROW[c.tipo]) for c in colunas])
    parquet = destino / f"{conjunto.nome}.parquet"
    csv_gz = destino / f"{conjunto.nome}.csv.gz"
    linhas = 0
    # Só esta consulta usa cursor no servidor (execution_options da conexão valeria para todas).
    resultado = conn.execute(
        text(conjunto.sql), execution_options={"stream_results": True, "yield_per": LOTE}
    )
    with (
        closing(resultado),  # fecha o cursor do servidor mesmo se algo falhar no meio
        pq.ParquetWriter(parquet, schema, compression="zstd") as pw,
        gzip.GzipFile(csv_gz, "wb", compresslevel=6, mtime=0) as bruto,
    ):
        arquivo_csv = _Texto(bruto)
        esperado = [c.nome for c in colunas]
        if list(resultado.keys()) != esperado:
            raise RuntimeError(
                f"{conjunto.nome}: colunas da consulta {list(resultado.keys())} "
                f"diferem do dicionário {esperado}"
            )
        saida = csv.writer(arquivo_csv, lineterminator="\n")
        saida.writerow(esperado)
        for lote in resultado.partitions(LOTE):
            cols = [[] for _ in colunas]
            for linha in lote:
                valores = [_valor(v, c.tipo, c.livre) for v, c in zip(linha, colunas, strict=True)]
                for i, v in enumerate(valores):
                    cols[i].append(v)
                saida.writerow([_celula_csv(v) for v in valores])
            pw.write_table(
                pa.Table.from_arrays(
                    [pa.array(v, type=schema.field(i).type) for i, v in enumerate(cols)],
                    schema=schema,
                )
            )
            linhas += len(lote)
    return {
        "linhas": linhas,
        "parquet": {"arquivo": parquet.name, "bytes": parquet.stat().st_size,
                    "sha256": sha256(parquet)},
        "csv_gz": {"arquivo": csv_gz.name, "bytes": csv_gz.stat().st_size,
                   "sha256": sha256(csv_gz)},
    }  # fmt: skip


class _Texto:
    """Adapta o arquivo gzip (bytes) para o csv.writer (texto UTF-8), sem acumular tudo."""

    def __init__(self, bruto):
        self.bruto = bruto

    def write(self, s: str) -> int:
        self.bruto.write(s.encode("utf-8"))
        return len(s)
