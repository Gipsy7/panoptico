"""Roda todas as ingestões. Uso: uv run python -m ingestion.run_all"""

import sys
import traceback
from collections.abc import Callable

from ingestion import comum
from ingestion.camara import deputados
from ingestion.camara import despesas as despesas_camara
from ingestion.senado import despesas as despesas_senado
from ingestion.senado import senadores


def _tarefas() -> list[tuple[str, Callable[[], int]]]:
    # Parlamentares primeiro: as demais cargas dependem deles.
    tarefas = [(deputados.FONTE, deputados.executar), (senadores.FONTE, senadores.executar)]
    for ano in comum.anos_padrao():
        for modulo in (despesas_camara, despesas_senado):
            tarefas.append((f"{modulo.FONTE} {ano}", lambda m=modulo, a=ano: m.executar(a)))
    return tarefas


def main() -> int:
    falhas = 0
    for nome, tarefa in _tarefas():
        try:
            print(f"[ok]   {nome}: {tarefa()} registros", flush=True)
        except Exception:
            falhas += 1
            print(f"[erro] {nome}", flush=True)
            traceback.print_exc()
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
