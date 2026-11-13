"""Toda rota fecha a sessão do banco ao terminar, antes de montar a resposta (app/db.py)."""

from fastapi.routing import APIRoute

from app.db import get_session
from app.main import app


def _dependencias(dependant):
    for dep in dependant.dependencies:
        yield dep
        yield from _dependencias(dep)


def test_sessao_com_escopo_da_funcao():
    erradas = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        for dep in _dependencias(route.dependant)
        if dep.call is get_session and dep.scope != "function"
    ]
    assert erradas == [], f"Use Depends(get_session, scope='function') em: {erradas}"
