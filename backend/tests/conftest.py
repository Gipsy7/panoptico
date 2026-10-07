import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Base
from app.services import cep

FIXTURES = Path(__file__).parent / "fixtures"


def carregar_fixture(nome: str):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _limpar_cache_cep():
    cep.limpar_cache()


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.test_database_url)
    try:
        eng.connect().close()
    except OperationalError:
        pytest.skip("Banco de teste indisponível (rode scripts/criar_banco.sql).")
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    with engine.connect() as conn:
        trans = conn.begin()
        sessao = sessionmaker(bind=conn, join_transaction_mode="create_savepoint")()
        yield sessao
        sessao.close()
        trans.rollback()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()
