from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Parlamentar(Base):
    __tablename__ = "parlamentar"
    __table_args__ = (
        UniqueConstraint("casa", "id_externo", name="uq_parlamentar_casa_id_externo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))  # "camara" | "senado"
    id_externo: Mapped[str] = mapped_column(String(20))
    nome_parlamentar: Mapped[str] = mapped_column(String(200))
    nome_civil: Mapped[str | None] = mapped_column(String(200))
    partido: Mapped[str | None] = mapped_column(String(30))
    uf: Mapped[str] = mapped_column(String(2), index=True)
    foto_url: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(100))
    pagina_url: Mapped[str | None] = mapped_column(String(500))
    em_exercicio: Mapped[bool] = mapped_column(Boolean, default=True)
    # Início do período atual de exercício (posse, posse de suplente ou retorno).
    em_exercicio_desde: Mapped[date | None] = mapped_column(Date)
    fonte_url: Mapped[str] = mapped_column(String(500))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
