"""Roda todas as ingestões. Uso: uv run python -m ingestion.run_all"""

import sys
import traceback

from ingestion.camara import deputados
from ingestion.senado import senadores

INGESTOES = [deputados, senadores]


def main() -> int:
    falhas = 0
    for modulo in INGESTOES:
        try:
            total = modulo.executar()
            print(f"[ok]   {modulo.FONTE}: {total} registros")
        except Exception:
            falhas += 1
            print(f"[erro] {modulo.FONTE}")
            traceback.print_exc()
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
