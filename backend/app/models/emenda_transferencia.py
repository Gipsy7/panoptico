from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmendaConvenio(Base):
    """Ligação emenda -> convênio, do arquivo de convênios das emendas (Portal da
    Transparência). Só diz qual convênio nasceu de qual emenda; os dados do convênio vêm
    de `emenda_transferencia`."""

    __tablename__ = "emenda_convenio"
    __table_args__ = (
        UniqueConstraint("emenda_codigo", "numero_convenio"),
        Index("ix_emenda_convenio_numero", "numero_convenio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    emenda_codigo: Mapped[str] = mapped_column(String(20))
    numero_convenio: Mapped[str] = mapped_column(String(20))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class EmendaTransferencia(Base):
    """O que aconteceu com o dinheiro de uma emenda: um convênio (Portal da Transparência)
    ou um plano de ação de transferência especial (TransfereGov), com situação, valores,
    vigência e andamento da prestação de contas."""

    __tablename__ = "emenda_transferencia"
    __table_args__ = (
        UniqueConstraint("tipo", "identificador", "emenda_codigo"),
        Index("ix_emenda_transferencia_emenda", "emenda_codigo"),
        Index("ix_emenda_transferencia_municipio", "municipio_ibge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))  # "convenio" | "especial"
    emenda_codigo: Mapped[str] = mapped_column(String(20))
    ano_emenda: Mapped[int] = mapped_column(SmallInteger)
    identificador: Mapped[str] = mapped_column(String(30))  # nº do convênio / código do plano
    situacao: Mapped[str | None] = mapped_column(String(120))
    relatorio_gestao: Mapped[str | None] = mapped_column(String(60))
    beneficiario: Mapped[str | None] = mapped_column(String(300))
    beneficiario_cnpj: Mapped[str | None] = mapped_column(String(20))
    uf: Mapped[str | None] = mapped_column(String(2))
    # Município do beneficiário (CNPJ -> IBGE); nulo para estados e CNPJ sem mapa.
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    orgao_concedente: Mapped[str | None] = mapped_column(String(200))
    objeto: Mapped[str | None] = mapped_column(Text)
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    valor_repassado: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    valor_contrapartida: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    inicio_vigencia: Mapped[date | None] = mapped_column(Date)
    fim_vigencia: Mapped[date | None] = mapped_column(Date)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
