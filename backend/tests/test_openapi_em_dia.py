"""O contrato da API que o site usa para gerar os tipos (frontend/lib/openapi.json) está em dia."""

from app.openapi_exportar import DESTINO, contrato


def test_openapi_em_dia():
    assert DESTINO.exists(), "Rode: python -m app.openapi_exportar"
    gravado = DESTINO.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert gravado == contrato(), (
        "A API mudou e frontend/lib/openapi.json não. Rode `python -m app.openapi_exportar` "
        "(dentro de backend) e depois `npm run tipos-api` (dentro de frontend)."
    )
