from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArrecadacaoUF(Base):
    """Arrecadação federal por estado e mês (Receita Federal, por domicílio fiscal do
    contribuinte). `total` soma todos os tributos; `previdencia` é a receita previdenciária."""

    __tablename__ = "arrecadacao_uf"

    uf: Mapped[str] = mapped_column(String(2), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    mes: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    previdencia: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    ingestao_id: Mapped[int | None] = mapped_column(
        ForeignKey("fonte_ingestao.id", ondelete="SET NULL")
    )


class PopulacaoIbge(Base):
    """População residente (IBGE): código de 1 dígito = Brasil, 2 = UF, 7 = município.
    `origem`: estimativa (SIDRA 6579) ou censo (SIDRA 9514, 2022)."""

    __tablename__ = "populacao_ibge"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    valor: Mapped[int] = mapped_column(BigInteger)
    origem: Mapped[str] = mapped_column(String(12))


class TransferenciaUniao(Base):
    """Repasse da União a estados e municípios por mês e bloco (FPE, FPM, IPI_EXP,
    FUNDEB_UNIAO, ROYALTIES, OUTRAS_OBRIG, LEGAIS_VOLUNTARIAS). `fonte`: tesouro ou portal."""

    __tablename__ = "transferencia_uniao"
    __table_args__ = (
        Index("ix_transferencia_uniao_ano_uf", "ano", "uf"),
        Index("ix_transferencia_uniao_municipio_ano", "municipio_ibge", "ano"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    mes: Mapped[int] = mapped_column(SmallInteger)
    uf: Mapped[str] = mapped_column(String(2))
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    bloco: Mapped[str] = mapped_column(String(24))
    fonte: Mapped[str] = mapped_column(String(16))
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    ingestao_id: Mapped[int | None] = mapped_column(
        ForeignKey("fonte_ingestao.id", ondelete="SET NULL")
    )
