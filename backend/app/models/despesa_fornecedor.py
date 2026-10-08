from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DespesaFornecedor(Base):
    """Quanto a prefeitura (ou a câmara) pagou a cada fornecedor no ano, segundo os dados
    abertos do Tribunal de Contas do estado. Só os maiores fornecedores por órgão; o resto
    vira uma linha "Demais fornecedores", e pagamentos a pessoas físicas ficam somados
    numa linha sem nomes."""

    __tablename__ = "despesa_fornecedor"
    __table_args__ = (Index("ix_despesa_fornecedor_municipio_ano", "municipio_ibge", "ano"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    municipio_ibge: Mapped[str] = mapped_column(ForeignKey("municipio.ibge", ondelete="CASCADE"))
    ano: Mapped[int] = mapped_column(SmallInteger)
    orgao: Mapped[str] = mapped_column(String(20))  # prefeitura, camara, outros
    fornecedor: Mapped[str] = mapped_column(String(300))
    documento: Mapped[str | None] = mapped_column(String(20))  # CNPJ (nunca CPF)
    valor_pago: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    pagamentos: Mapped[int]
    fonte: Mapped[str] = mapped_column(String(20))  # tce_sp, tce_rs...
