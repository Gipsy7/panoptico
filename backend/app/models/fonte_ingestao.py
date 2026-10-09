from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FonteIngestao(Base):
    """Uma execução de ingestão: de onde veio o dado, quando e onde está o bruto."""

    __tablename__ = "fonte_ingestao"

    id: Mapped[int] = mapped_column(primary_key=True)
    fonte: Mapped[str] = mapped_column(String(50), index=True)
    url: Mapped[str] = mapped_column(String(500))
    arquivo_raw: Mapped[str] = mapped_column(String(500))
    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registros: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(20), default="em_andamento")
    # Conferência da carga (opcionais): total que a própria fonte informa (ou o número de
    # linhas do arquivo) e avisos de qualidade (campo-chave nulo, duplicatas, total que não bate).
    total_fonte: Mapped[int | None] = mapped_column(BigInteger)
    alertas: Mapped[list | None] = mapped_column(JSON)


class DownloadCache(Base):
    """O que se sabe do último download de uma URL (ou de um conjunto de URLs): validadores
    HTTP e sha256, para não baixar nem recarregar o que não mudou."""

    __tablename__ = "download_cache"

    chave: Mapped[str] = mapped_column(String(500), primary_key=True)
    url: Mapped[str | None] = mapped_column(String(500))
    etag: Mapped[str | None] = mapped_column(String(300))
    last_modified: Mapped[str | None] = mapped_column(String(100))
    sha256: Mapped[str | None] = mapped_column(String(64))
    tamanho: Mapped[int | None] = mapped_column(BigInteger)
    contexto: Mapped[str | None] = mapped_column(String(200))
    baixado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
