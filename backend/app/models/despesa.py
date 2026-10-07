from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Despesa(Base):
    """Gasto da cota parlamentar (CEAP na Câmara, CEAPS no Senado)."""

    __tablename__ = "despesa"
    __table_args__ = (
        Index("ix_despesa_parlamentar_ano", "parlamentar_id", "ano"),
        Index("ix_despesa_casa_ano", "casa", "ano"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parlamentar_id: Mapped[int] = mapped_column(ForeignKey("parlamentar.id", ondelete="CASCADE"))
    casa: Mapped[str] = mapped_column(String(10))
    ano: Mapped[int] = mapped_column(SmallInteger)
    mes: Mapped[int] = mapped_column(SmallInteger)
    categoria: Mapped[str] = mapped_column(String(300))
    fornecedor: Mapped[str | None] = mapped_column(String(300))
    cnpj_cpf: Mapped[str | None] = mapped_column(String(30))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data: Mapped[date | None] = mapped_column(Date)
    url_documento: Mapped[str | None] = mapped_column(String(500))
    id_externo: Mapped[str | None] = mapped_column(String(30))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
