"""Contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). Só totais por dia: sem IP, sem
user-agent, sem identificador de pessoa, navegador ou sessão e sem hora. Nada daqui vai para a
API pública de leitura nem para a exportação aberta."""

from datetime import date

from sqlalchemy import BigInteger, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetricaDiaria(Base):
    __tablename__ = "metrica_diaria"

    dia: Mapped[date] = mapped_column(Date, primary_key=True)
    # pagina | visita | origem | dispositivo | recurso
    tipo: Mapped[str] = mapped_column(String(12), primary_key=True)
    chave: Mapped[str] = mapped_column(String(120), primary_key=True)
    total: Mapped[int] = mapped_column(BigInteger, default=0)
