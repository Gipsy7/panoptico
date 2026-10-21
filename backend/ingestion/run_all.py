"""Roda todas as ingestões. Uso: uv run python -m ingestion.run_all"""

import os
import sys
import time
import traceback
from collections.abc import Callable

from ingestion import comum, limpar_raw, resumos
from ingestion.camara import deputados
from ingestion.camara import despesas as despesas_camara
from ingestion.camara import discursos as discursos_camara
from ingestion.camara import proposicoes as proposicoes_camara
from ingestion.camara import temas as temas_camara
from ingestion.camara import votacoes as votacoes_camara
from ingestion.canais import catalogo as canais
from ingestion.congresso import emendas_relator
from ingestion.ibge import municipios
from ingestion.senado import despesas as despesas_senado
from ingestion.senado import discursos as discursos_senado
from ingestion.senado import proposicoes as proposicoes_senado
from ingestion.senado import senadores
from ingestion.senado import temas as temas_senado
from ingestion.senado import votacoes as votacoes_senado
from ingestion.senado import votacoes_comissoes as comissoes_senado
from ingestion.transferegov import convenios as convenios_emendas
from ingestion.transferegov import especiais as especiais_emendas
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
    # Depois das votações: só ficam os discursos de dia de votação nominal (incrementais).
    tarefas.append((discursos_camara.FONTE, discursos_camara.executar))
    tarefas.append((discursos_senado.FONTE, discursos_senado.executar))
    tarefas.append((municipios.FONTE, municipios.executar))
    tarefas.append((canais.FONTE, canais.executar))  # catálogo versionado; não acessa sites
    tarefas.append((emendas.FONTE, emendas.executar))
    tarefas.append((emendas_relator.FONTE, emendas_relator.executar))  # indicações RP9 (2022)
    # Depois das emendas: o que aconteceu com o dinheiro (convênios e transferências especiais).
    tarefas.append((convenios_emendas.FONTE, convenios_emendas.executar))
    tarefas.append((especiais_emendas.FONTE, especiais_emendas.executar))
    # Por último: consolida os números de cada parlamentar a partir do que foi carregado.
    tarefas.append((resumos.FONTE, resumos.executar))
    return tarefas


ESPERA_PADRAO = 120.0  # segundos entre a 1ª e a 2ª passada


def _espera_segunda_passada() -> float:
    """INGESTAO_ESPERA_SEGUNDA_PASSADA (segundos) muda a espera; 0 zera (testes)."""
    try:
        return max(0.0, float(os.environ.get("INGESTAO_ESPERA_SEGUNDA_PASSADA", ESPERA_PADRAO)))
    except ValueError:
        return ESPERA_PADRAO


def _passada(tarefas: list[tuple[str, Callable[[], int]]]) -> list[tuple[str, Callable[[], int]]]:
    """Roda as tarefas e devolve as que falharam."""
    falharam = []
    for nome, tarefa in tarefas:
        try:
            print(f"[ok]   {nome}: {tarefa()} registros", flush=True)
        except Exception:
            falharam.append((nome, tarefa))
            print(f"[erro] {nome}", flush=True)
            traceback.print_exc()
    return falharam


def _resumo(primeira: list[str], recuperadas: list[str], persistentes: list[str]) -> None:
    """Escreve o resumo no painel do GitHub Actions (GITHUB_STEP_SUMMARY), se existir."""
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if not caminho or not primeira:
        return
    linhas = ["## Ingestão diária: fontes que falharam na 1ª passada", ""]
    linhas += [f"- {n}" for n in primeira]
    linhas += ["", "### Recuperadas na 2ª passada", ""]
    linhas += [f"- {n}" for n in recuperadas] or ["- nenhuma"]
    linhas += ["", "### Falharam também na 2ª passada", ""]
    linhas += [f"- {n}" for n in persistentes] or ["- nenhuma"]
    with open(caminho, "a", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


def main() -> int:
    tarefas = _tarefas()
    falharam = _passada(tarefas)
    primeira = [n for n, _ in falharam]
    persistentes = primeira
    if falharam:
        espera = _espera_segunda_passada()
        print(f"[2ª passada] {len(falharam)} tarefa(s) a repetir em {espera:g} s", flush=True)
        time.sleep(espera)
        persistentes_tarefas = _passada(falharam)
        persistentes = [n for n, _ in persistentes_tarefas]
        recuperadas = [n for n in primeira if n not in persistentes]
        if recuperadas:
            # Os resumos consolidam o que foi carregado: refaz depois de recuperar dados.
            for nome, tarefa in tarefas:
                if nome == resumos.FONTE and nome not in primeira:
                    _passada([(nome, tarefa)])
        _resumo(primeira, recuperadas, persistentes)
    print(f"[ok]   brutos antigos apagados: {len(limpar_raw.limpar())}", flush=True)
    return 1 if persistentes else 0


if __name__ == "__main__":
    sys.exit(main())
