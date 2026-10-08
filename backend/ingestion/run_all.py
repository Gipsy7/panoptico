"""Roda todas as ingestões. Uso: uv run python -m ingestion.run_all"""

import sys
import traceback
from collections.abc import Callable

from ingestion import comum, limpar_raw, resumos
from ingestion.camara import deputados
from ingestion.camara import despesas as despesas_camara
from ingestion.camara import proposicoes as proposicoes_camara
from ingestion.camara import temas as temas_camara
from ingestion.camara import votacoes as votacoes_camara
from ingestion.canais import catalogo as canais
from ingestion.ibge import municipios
from ingestion.senado import despesas as despesas_senado
from ingestion.senado import proposicoes as proposicoes_senado
from ingestion.senado import senadores
from ingestion.senado import temas as temas_senado
from ingestion.senado import votacoes as votacoes_senado
from ingestion.senado import votacoes_comissoes as comissoes_senado
from ingestion.transparencia import emendas


def _tarefas() -> list[tuple[str, Callable[[], int]]]:
    # Parlamentares primeiro: as demais cargas dependem deles.
    tarefas = [(deputados.FONTE, deputados.executar), (senadores.FONTE, senadores.executar)]
    for ano in comum.anos_padrao():
        for modulo in (
            despesas_camara,
            despesas_senado,
            votacoes_camara,
            votacoes_senado,
            comissoes_senado,
        ):
            tarefas.append((f"{modulo.FONTE} {ano}", lambda m=modulo, a=ano: m.executar(a)))
        tarefas.append((f"camara_proposicoes {ano}", lambda a=ano: proposicoes_camara.executar(a)))
    tarefas.append((proposicoes_senado.FONTE, proposicoes_senado.executar))
    # Depois das votações: busca na API os temas das matérias votadas que faltarem.
    tarefas.append((temas_camara.FONTE, temas_camara.executar))
    tarefas.append((temas_senado.FONTE, temas_senado.executar))
    tarefas.append((municipios.FONTE, municipios.executar))
    tarefas.append((canais.FONTE, canais.executar))  # catálogo versionado; não acessa sites
    tarefas.append((emendas.FONTE, emendas.executar))
    # Por último: consolida os números de cada parlamentar a partir do que foi carregado.
    tarefas.append((resumos.FONTE, resumos.executar))
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
    print(f"[ok]   brutos antigos apagados: {len(limpar_raw.limpar())}", flush=True)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
