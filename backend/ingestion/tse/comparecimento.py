"""Comparecimento, brancos e nulos por cargo, município e turno (detalhe_votacao_munzona do TSE).

A carga mora em `ingestion.tse.resultados` (as duas tabelas da Frente 5 andam juntas); este
módulo só dá a ela um nome próprio no registro de fontes e em fonte_ingestao.
"""

import argparse

from ingestion.tse.resultados import FONTE_TOTAIS as FONTE
from ingestion.tse.resultados import executar_totais as executar

__all__ = ["FONTE", "executar"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Ingestão: {FONTE}")
    parser.add_argument("--ano", type=int, nargs="*", default=[2022, 2024, 2026])
    args = parser.parse_args()
    for ano in args.ano:
        print(f"{FONTE} {ano}: {executar(ano)} linhas")
