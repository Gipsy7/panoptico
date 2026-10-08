from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CanalOficial(Base):
    """Site oficial de um município (prefeitura, câmara, portal da transparência), vindo do
    catálogo versionado data/canais_oficiais.csv (gerado pela varredura e revisado por PR)."""

    __tablename__ = "canal_oficial"

    id: Mapped[int] = mapped_column(primary_key=True)
    municipio_ibge: Mapped[str] = mapped_column(
        ForeignKey("municipio.ibge", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(40))  # prefeitura, camara, transparencia_...
    url: Mapped[str] = mapped_column(Text)
    sistema: Mapped[str | None] = mapped_column(String(40))  # sapl, betha, ipm...
    verificado_em: Mapped[date | None] = mapped_column(Date)
