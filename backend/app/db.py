from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
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
    # Espera curta por conexão: com o pool cheio, melhor um erro rápido do que pedidos presos.
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_timeout=10)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Sessão de uma rota. Nas rotas, use o tipo `Sessao` (abaixo).

    Com o escopo padrão ("request") a sessão só fecha depois de a resposta ser enviada, e a
    resposta de rota síncrona é montada numa thread do mesmo grupo de 40 que espera conexão:
    com muitos pedidos juntos, quem tem conexão espera thread e quem tem thread espera conexão
    (em 13/11/2026 isso travou a API da produção). Com "function" a conexão volta ao pool assim
    que a rota termina.
    """
    with SessionLocal() as session:
        yield session


# Tipo da sessão nas rotas, já com o escopo certo.
Sessao = Annotated[Session, Depends(get_session, scope="function")]
