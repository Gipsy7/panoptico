from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ServidorFederal(Base):
    """Um cargo de confiança (cargo comissionado ou função de confiança) de uma pessoa da
    base no cadastro mensal de servidores do Portal da Transparência (SIAPE). Só as pessoas
    que acompanhamos, ligadas por CPF parcial + nome. `primeiro_mes` e `ultimo_mes` são os
    meses do cadastro em que o registro apareceu: se `ultimo_mes` ficou para trás do mês mais
    recente carregado, a pessoa deixou de constar no cargo."""

    __tablename__ = "servidor_federal"
    __table_args__ = (UniqueConstraint("id_externo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="CASCADE"), index=True)
    id_externo: Mapped[str] = mapped_column(String(100))
    id_portal: Mapped[int] = mapped_column(Integer)  # Id_SERVIDOR_PORTAL (link do Portal)
    sigla: Mapped[str] = mapped_column(String(10))  # CCX, FEX, CD, DAS...
    nivel: Mapped[str | None] = mapped_column(String(6))
    funcao: Mapped[str] = mapped_column(String(120))
    atividade: Mapped[str | None] = mapped_column(String(120))
    orgao: Mapped[str | None] = mapped_column(String(120))
    orgao_superior: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    situacao_vinculo: Mapped[str | None] = mapped_column(String(60))
    data_ingresso: Mapped[date | None] = mapped_column(Date)
    data_nomeacao: Mapped[date | None] = mapped_column(Date)
    primeiro_mes: Mapped[date] = mapped_column(Date)
    ultimo_mes: Mapped[date] = mapped_column(Date)


class ViagemFederalAno(Base):
    """Viagens a serviço de uma pessoa da base (Portal da Transparência), somadas por ano
    da viagem: sem destino, motivo nem trecho (coleta mínima; o detalhe está a um link)."""

    __tablename__ = "viagem_federal_ano"
    __table_args__ = (UniqueConstraint("pessoa_id", "ano"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="CASCADE"))
    ano: Mapped[int] = mapped_column(Integer)
    viagens: Mapped[int] = mapped_column(Integer)
    diarias: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    passagens: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    outros: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    devolucao: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ultima_viagem: Mapped[date | None] = mapped_column(Date)  # início da última viagem do ano
