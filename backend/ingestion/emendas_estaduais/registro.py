"""Os adaptadores de emendas estaduais por UF (um por fonte). Ver base.py.

`python -m ingestion.emendas_estaduais.registro [--uf MG BA]` roda as cargas em sequência
(todas, sem --uf); cada uma é uma transação própria e a falha de uma não para as outras."""

import argparse
import sys
from types import ModuleType

from ingestion.emendas_estaduais import ac, al, ba, es, ma, mg, pe, sc, se

# Ordem: as que cobrem mais gente primeiro.
ADAPTADORES: dict[str, ModuleType] = {
    "MG": mg,
    "BA": ba,
    "PE": pe,
    "SC": sc,
    "MA": ma,
    "ES": es,
    "AL": al,
    "SE": se,
    "AC": ac,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestão: emendas estaduais por UF")
    parser.add_argument("--uf", nargs="*", help="UFs (padrão: todas com fonte aberta)")
    args = parser.parse_args()
    falhas = []
    for uf in [u.upper() for u in args.uf] if args.uf else list(ADAPTADORES):
        try:
            total = ADAPTADORES[uf].executar()
            print(f"emendas estaduais {uf}: {total} linhas")
        except Exception as erro:  # registra e segue para a próxima UF
            print(f"emendas estaduais {uf}: falhou ({erro})", file=sys.stderr)
            falhas.append(uf)
    if falhas:
        sys.exit(f"Falharam: {', '.join(falhas)}")


if __name__ == "__main__":
    main()
