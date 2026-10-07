from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Votacao(Base):
    """Votação nominal no Plenário da Câmara ou do Senado."""

    __tablename__ = "votacao"
    __table_args__ = (
        UniqueConstraint("casa", "id_externo", name="uq_votacao_casa_id_externo"),
        Index("ix_votacao_casa_data", "casa", "data"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    id_externo: Mapped[str] = mapped_column(String(30))
    data: Mapped[date] = mapped_column(Date)
    descricao: Mapped[str] = mapped_column(Text)
    proposicao: Mapped[str | None] = mapped_column(String(40))
    secreta: Mapped[bool] = mapped_column(Boolean, default=False)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class Voto(Base):
    """Registro de um parlamentar numa votação. Na Câmara só existe para quem votou; no
    Senado existe para todos os senadores, com o código de ausência quando é o caso."""

    __tablename__ = "voto"

    votacao_id: Mapped[int] = mapped_column(
        ForeignKey("votacao.id", ondelete="CASCADE"), primary_key=True
    )
    parlamentar_id: Mapped[int] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    voto: Mapped[str] = mapped_column(String(60))
