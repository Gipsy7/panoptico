"""Grava o contrato da API (OpenAPI) em frontend/lib/openapi.json, de onde o site gera os tipos.

    python -m app.openapi_exportar

Rode sempre que mudar uma rota ou um esquema de resposta; o teste `test_openapi_em_dia` falha
enquanto o arquivo estiver diferente da API. Depois, no frontend: `npm run tipos-api`.
"""

import json
import sys
from pathlib import Path

from app.main import app

DESTINO = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "openapi.json"


def contrato() -> str:
    """O OpenAPI em texto estável: chaves em ordem e uma quebra de linha no fim."""
    return json.dumps(app.openapi(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    DESTINO.write_text(contrato(), encoding="utf-8", newline="\n")
    print(f"gravado: {DESTINO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
