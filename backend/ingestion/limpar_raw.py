"""Apaga arquivos brutos antigos, mantendo os mais recentes de cada fonte (e de cada ano,
nas fontes anuais). Uso: uv run python -m ingestion.limpar_raw [--manter 7]"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

from ingestion.comum import RAW_DIR

# "2026_2026-10-06_212345.csv.gz" -> grupo "2026_"; "2026-10-06_212345.json" -> grupo ""
NOME = re.compile(r"^(?P<grupo>(?:\d{4}_)?)\d{4}-\d{2}-\d{2}_\d{6}\.")


def limpar(raiz: Path = RAW_DIR, manter: int = 7) -> list[Path]:
    grupos: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for arquivo in raiz.glob("*/*"):
        m = NOME.match(arquivo.name)
        if arquivo.is_file() and m:
            grupos[(arquivo.parent, m["grupo"])].append(arquivo)
    apagados = []
    for arquivos in grupos.values():
        # O nome tem data e hora, então a ordem alfabética é a cronológica.
        for antigo in sorted(arquivos, key=lambda a: a.name)[:-manter]:
            antigo.unlink()
            apagados.append(antigo)
    return apagados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apaga brutos antigos")
    parser.add_argument("--manter", type=int, default=7)
    args = parser.parse_args()
    print(f"{len(limpar(manter=args.manter))} arquivos brutos apagados")
