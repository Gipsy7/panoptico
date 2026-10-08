from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContasMunicipio(Base):
    """Contas anuais do município entregues ao Tesouro (SICONFI, Declaração de Contas
    Anuais): receita realizada, despesa paga e despesa paga por função (área). Uma linha
    por município e ano."""

    __tablename__ = "contas_municipio"

    municipio_ibge: Mapped[str] = mapped_column(
        ForeignKey("municipio.ibge", ondelete="CASCADE"), primary_key=True
    )
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    populacao: Mapped[int | None]
    receita_total: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    despesa_paga: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    # {"Saúde": 123.45, "Educação": ...}: despesa paga por função de governo.
    despesa_por_area: Mapped[dict] = mapped_column(JSON)
