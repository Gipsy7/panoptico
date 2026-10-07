from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Proposicao(Base):
    """Projeto de lei (PL, PLP, PEC, PDL) apresentado na Câmara ou no Senado."""

    __tablename__ = "proposicao"
    __table_args__ = (UniqueConstraint("casa", "id_externo", name="uq_proposicao_casa_id_externo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    id_externo: Mapped[str] = mapped_column(String(30))
    sigla_tipo: Mapped[str] = mapped_column(String(10))
    numero: Mapped[int]
    ano: Mapped[int] = mapped_column(SmallInteger)
    ementa: Mapped[str] = mapped_column(Text)
    data_apresentacao: Mapped[date] = mapped_column(Date, index=True)
    situacao: Mapped[str | None] = mapped_column(String(200))
    virou_lei: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str] = mapped_column(String(500))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class Autoria(Base):
    __tablename__ = "autoria"

    proposicao_id: Mapped[int] = mapped_column(
        ForeignKey("proposicao.id", ondelete="CASCADE"), primary_key=True
    )
    parlamentar_id: Mapped[int] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    primeiro_autor: Mapped[bool] = mapped_column(Boolean)
