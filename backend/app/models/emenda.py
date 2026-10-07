from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Emenda(Base):
    """Emenda parlamentar ao orçamento federal (Portal da Transparência).

    Cada linha é uma emenda numa localidade e ação; o mesmo código pode se repetir."""

    __tablename__ = "emenda"
    __table_args__ = (
        Index("ix_emenda_municipio_ano", "municipio_ibge", "ano"),
        Index("ix_emenda_parlamentar_ano", "parlamentar_id", "ano"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), index=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    tipo: Mapped[str] = mapped_column(String(100))
    individual: Mapped[bool]
    autor_codigo: Mapped[str] = mapped_column(String(20))
    autor_nome: Mapped[str] = mapped_column(String(200))
    parlamentar_id: Mapped[int | None] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="SET NULL")
    )
    localidade: Mapped[str] = mapped_column(String(200))
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    uf: Mapped[str | None] = mapped_column(String(50))
    funcao: Mapped[str | None] = mapped_column(String(100))
    acao: Mapped[str | None] = mapped_column(String(300))
    valor_empenhado: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_pago: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
