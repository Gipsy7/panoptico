"""Fichas das proposições votadas no Plenário que faltam na tabela `proposicao` (anteriores a
2023, MPV...). Módulo próprio para o registro de fontes, que chama `executar()`; a lógica fica em
`ingestion.camara.proposicoes`."""

from ingestion.camara.proposicoes import FONTE_VOTADAS as FONTE
from ingestion.camara.proposicoes import executar_votadas as executar

__all__ = ["FONTE", "executar"]

if __name__ == "__main__":
    print(f"{FONTE}: {executar()} proposições")
