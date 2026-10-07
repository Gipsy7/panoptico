from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmendaPagamento(Base):
    """Valor de emenda individual recebido por prefeitura, fundo municipal ou entidade
    sem fins lucrativos de um município (Portal da Transparência, por favorecido)."""

    __tablename__ = "emenda_pagamento"
    __table_args__ = (
        Index("ix_emenda_pagamento_municipio", "municipio_ibge", "ano_emenda"),
        Index("ix_emenda_pagamento_parlamentar", "parlamentar_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    emenda_codigo: Mapped[str] = mapped_column(String(20))
    ano_emenda: Mapped[int] = mapped_column(SmallInteger)
    ano_mes: Mapped[int] = mapped_column(Integer)
    autor_codigo: Mapped[str] = mapped_column(String(20))
    autor_nome: Mapped[str] = mapped_column(String(200))
    parlamentar_id: Mapped[int | None] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="SET NULL")
    )
    favorecido: Mapped[str] = mapped_column(String(300))
    favorecido_codigo: Mapped[str] = mapped_column(String(20))
    natureza: Mapped[str] = mapped_column(String(100))
    grupo: Mapped[str] = mapped_column(String(20))  # "prefeitura" | "entidade"
    municipio_ibge: Mapped[str] = mapped_column(ForeignKey("municipio.ibge"))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
