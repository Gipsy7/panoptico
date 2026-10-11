from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmendaRelatorIndicacao(Base):
    """Indicação de beneficiário de emenda de relator-geral (RP9) registrada na planilha
    oficial da Comissão Mista de Orçamento (LOA 2022), com o parlamentar que pediu.

    Só ficam as indicações cujo autor (deputado ou senador) foi ligado a um parlamentar da
    base. O valor é o solicitado/indicado; a planilha não traz empenho nem pagamento."""

    __tablename__ = "emenda_relator_indicacao"
    __table_args__ = (Index("ix_emenda_relator_parlamentar", "parlamentar_id", "ano"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    data_cadastro: Mapped[date | None] = mapped_column(Date)
    parlamentar_id: Mapped[int] = mapped_column(ForeignKey("parlamentar.id", ondelete="CASCADE"))
    autor_nome: Mapped[str] = mapped_column(String(200))
    beneficiario: Mapped[str] = mapped_column(String(300))
    beneficiario_cnpj: Mapped[str | None] = mapped_column(String(20))
    uf: Mapped[str | None] = mapped_column(String(2))
    orgao: Mapped[str | None] = mapped_column(String(150))
    unidade: Mapped[str | None] = mapped_column(String(200))
    acao: Mapped[str | None] = mapped_column(String(20))
    objeto: Mapped[str | None] = mapped_column(String(500))
    valor_solicitado: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
