"""Roda todas as ingestões. Uso: uv run python -m ingestion.run_all"""

import sys
import traceback
from collections.abc import Callable

from ingestion import comum
from ingestion.camara import deputados
from ingestion.camara import despesas as despesas_camara
from ingestion.camara import proposicoes as proposicoes_camara
from ingestion.camara import votacoes as votacoes_camara
from ingestion.senado import despesas as despesas_senado
from ingestion.senado import proposicoes as proposicoes_senado
from ingestion.senado import senadores
from ingestion.senado import votacoes as votacoes_senado


def _tarefas() -> list[tuple[str, Callable[[], int]]]:
    # Parlamentares primeiro: as demais cargas dependem deles.
    tarefas = [(deputados.FONTE, deputados.executar), (senadores.FONTE, senadores.executar)]
    for ano in comum.anos_padrao():
        for modulo in (despesas_camara, despesas_senado, votacoes_camara, votacoes_senado):
            tarefas.append((f"{modulo.FONTE} {ano}", lambda m=modulo, a=ano: m.executar(a)))
        tarefas.append((f"camara_proposicoes {ano}", lambda a=ano: proposicoes_camara.executar(a)))
    tarefas.append((proposicoes_senado.FONTE, proposicoes_senado.executar))
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
