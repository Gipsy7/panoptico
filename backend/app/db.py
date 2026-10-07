from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

if settings.serverless:
    # Uma conexão por requisição; o pooler do Neon (PgBouncer) cuida do reaproveitamento.
    # Sem prepared statements, que não combinam com pooling em modo transação.
    engine = create_engine(
        settings.database_url, poolclass=NullPool, connect_args={"prepare_threshold": None}
    )
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
