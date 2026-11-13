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


def test_sessao_da_rota_tem_teto_de_consulta(engine, monkeypatch):
    """A sessão das rotas cancela consulta que passa do teto; 0 desliga (app/config.py)."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app import db

    monkeypatch.setattr(db, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(db.settings, "api_statement_timeout_ms", 1234)
    sessao = next(gerador := db.get_session())
    assert sessao.scalar(text("SHOW statement_timeout")) == "1234ms"
    gerador.close()

    monkeypatch.setattr(db.settings, "api_statement_timeout_ms", 0)
    sessao = next(gerador := db.get_session())
    assert sessao.scalar(text("SHOW statement_timeout")) != "1234ms"
    gerador.close()
