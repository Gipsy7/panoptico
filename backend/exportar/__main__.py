"""python -m exportar --destino <pasta> [--conjunto nome ...] [--listar]"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import settings
from exportar.conjuntos import CONJUNTOS, POR_NOME
from exportar.documentacao import escrever_documentacao
from exportar.escrita import exportar_conjunto


def principal(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m exportar", description=__doc__)
    ap.add_argument("--destino", type=Path, help="pasta onde gravar (criada se não existir)")
    ap.add_argument("--conjunto", nargs="+", metavar="NOME", help="só estes conjuntos")
    ap.add_argument("--listar", action="store_true", help="lista os conjuntos e sai")
    args = ap.parse_args(argv)

    if args.listar:
        for c in CONJUNTOS:
            print(f"{c.nome:28} {c.titulo}")
        return 0
    if args.destino is None:
        ap.error("--destino é obrigatório")
    escolhidos = CONJUNTOS
    if args.conjunto:
        desconhecidos = [n for n in args.conjunto if n not in POR_NOME]
        if desconhecidos:
            ap.error(f"conjunto desconhecido: {', '.join(desconhecidos)} (use --listar)")
        escolhidos = tuple(POR_NOME[n] for n in args.conjunto)

    args.destino.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url)
    print(f"Banco: {engine.url.render_as_string(hide_password=True)}", flush=True)
    resultados = {}
    with engine.connect() as conn:
        # Uma transação só, de leitura: o conjunto inteiro sai de um retrato consistente,
        # mesmo com uma carga rodando no banco.
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        for c in escolhidos:
            r = exportar_conjunto(conn, c, args.destino)
            resultados[c.nome] = r
            print(
                f"{c.nome:28} {r['linhas']:>10} linhas  "
                f"parquet {r['parquet']['bytes']:>12,}  csv.gz {r['csv_gz']['bytes']:>12,}",
                flush=True,
            )
        escrever_documentacao(conn, escolhidos, resultados, args.destino)
    print(f"Pronto: {args.destino}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
