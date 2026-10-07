from datetime import datetime

from sqlalchemy import DateTime, String, func
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
