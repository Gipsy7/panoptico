from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ResumoParlamentar(Base):
    """Números de cada parlamentar num ano, recalculados ao fim de cada ingestão
    (ingestion/resumos.py). Servem a lista ordenável e o comparador sem refazer contas
    pesadas a cada acesso. Projetos e emendas cobrem a legislatura toda e se repetem em
    cada ano."""

    __tablename__ = "resumo_parlamentar"

    parlamentar_id: Mapped[int] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="CASCADE"), primary_key=True
    )
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    gastos: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    presenca_votou: Mapped[int] = mapped_column(default=0)
    presenca_total: Mapped[int] = mapped_column(default=0)
    governo_iguais: Mapped[int] = mapped_column(default=0)
    governo_total: Mapped[int] = mapped_column(default=0)
    partido_iguais: Mapped[int] = mapped_column(default=0)
    partido_total: Mapped[int] = mapped_column(default=0)
    projetos: Mapped[int] = mapped_column(default=0)  # autor principal, sem homenagens
    homenagens: Mapped[int] = mapped_column(default=0)  # autor principal, só homenagens
    normas: Mapped[int] = mapped_column(default=0)  # autor principal, viraram norma
    emendas_pagas: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
