"""Análises (cruzamentos) versionadas: cada arquivo `analises/<nome>.sql` é uma consulta
nomeada, com a explicação de como ler o resultado no comentário do topo.

Uso:
    python -m analises                       # lista as análises
    python -m analises fornecedores_sancionados [--saida resultado.csv]

O resultado é um CSV (na saída padrão ou no arquivo). Uma análise que se mostrar sólida
vira rota da API e depois seção do site; até lá, é material de conferência.
"""

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import text

from app.db import SessionLocal

PASTA = Path(__file__).parent


def disponiveis() -> dict[str, str]:
    """Nome -> primeira linha do comentário do topo."""
    resultado = {}
    for arquivo in sorted(PASTA.glob("*.sql")):
        primeira = next(
            (
                linha
                for linha in arquivo.read_text(encoding="utf-8").splitlines()
                if linha.startswith("--")
            ),
            "",
        )
        resultado[arquivo.stem] = primeira.lstrip("- ").strip()
    return resultado


def rodar(nome: str, saida) -> int:
    consulta = (PASTA / f"{nome}.sql").read_text(encoding="utf-8")
    with SessionLocal() as session:
        resultado = session.execute(text(consulta))
        escritor = csv.writer(saida)
        escritor.writerow(resultado.keys())
        linhas = 0
        for linha in resultado:
            escritor.writerow(linha)
            linhas += 1
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Análises do Panóptico")
    parser.add_argument("nome", nargs="?", help="Nome da análise (sem .sql)")
    parser.add_argument("--saida", type=Path, help="Arquivo CSV de saída (padrão: tela)")
    args = parser.parse_args(argv)
    analises = disponiveis()
    if not args.nome:
        for nome, descricao in analises.items():
            print(f"{nome:32} {descricao}")
        return 0
    if args.nome not in analises:
        parser.error(f"análise desconhecida: {args.nome}")
    if args.saida:
        with args.saida.open("w", encoding="utf-8", newline="") as arquivo:
            linhas = rodar(args.nome, arquivo)
    else:
        linhas = rodar(args.nome, sys.stdout)
    print(f"{linhas} linhas", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
