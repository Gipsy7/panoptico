"""Diz se as migrações aplicadas entre duas versões do banco pedem a recarga completa dos
dados federais (run_all), usado pelo workflow Publicar.

Uma migração só pede recarga se declarar `RECARREGAR_DADOS = True`: é o caso de quem muda
tabelas que a ingestão diária preenche (ex.: coluna nova calculada a partir dos dados).
Tabelas novas, com carga própria, não pedem: a publicação fica em poucos minutos.

Uso: python -m ingestion.precisa_recarga <versão antes> <versão depois>  -> imprime true/false
"""

import importlib.util
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import BACKEND_DIR


def precisa(antes: str | None, depois: str) -> bool:
    scripts = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini")))
    for revisao in scripts.iterate_revisions(depois, antes or "base"):
        if revisao.revision == antes:
            continue
        spec = importlib.util.spec_from_file_location(revisao.revision, revisao.path)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        if getattr(modulo, "RECARREGAR_DADOS", False):
            return True
    return False


if __name__ == "__main__":
    antes = sys.argv[1] if len(sys.argv) > 2 and sys.argv[1] not in ("", "None") else None
    print("true" if precisa(antes, sys.argv[-1]) else "false")
