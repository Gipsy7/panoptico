from decimal import Decimal

from sqlalchemy import (
    JSON,
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


class Candidatura(Base):
    """Uma candidatura registrada no TSE (arquivo consulta_cand).

    Guardamos as candidaturas dos parlamentares em exercício (ligadas pelo CPF, em qualquer
    eleição e cargo) e, a partir da fase B, as dos eleitos para câmaras municipais e
    assembleias. O CPF serve só para casar registros entre eleições e nunca é exibido.
    """

    __tablename__ = "candidatura"
    __table_args__ = (
        UniqueConstraint("ano_eleicao", "sq_candidato"),
        Index("ix_candidatura_cpf", "cpf"),
        Index("ix_candidatura_municipio_ibge", "municipio_ibge"),
        Index("ix_candidatura_cargo_uf", "cargo", "uf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ano_eleicao: Mapped[int] = mapped_column(SmallInteger)
    sq_candidato: Mapped[str] = mapped_column(String(20))
    cargo: Mapped[str] = mapped_column(String(40))
    uf: Mapped[str] = mapped_column(String(2))
    unidade: Mapped[str] = mapped_column(String(100))  # estado ou município da disputa
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    nome: Mapped[str] = mapped_column(String(200))
    nome_urna: Mapped[str] = mapped_column(String(100))
    partido: Mapped[str | None] = mapped_column(String(30))
    numero: Mapped[str | None] = mapped_column(String(10))
    situacao_turno: Mapped[str | None] = mapped_column(String(40))  # ELEITO, SUPLENTE...
    situacao_candidatura: Mapped[str | None] = mapped_column(String(40))  # APTO, INAPTO...
    cpf: Mapped[str | None] = mapped_column(String(11))
    # Para vices: a candidatura do titular da mesma chapa.
    chapa_titular_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidatura.id", ondelete="SET NULL")
    )
    parlamentar_id: Mapped[int | None] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="SET NULL"), index=True
    )
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class BemDeclarado(Base):
    """Bem declarado pelo candidato ao TSE (arquivo bem_candidato), valor como declarado."""

    __tablename__ = "bem_declarado"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidatura_id: Mapped[int] = mapped_column(
        ForeignKey("candidatura.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int] = mapped_column(SmallInteger)
    tipo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class CampanhaResumo(Base):
    """Totais da prestação de contas da campanha. Só os agregados: o detalhe (cada receita e
    despesa) fica no arquivo oficial, e nomes de doadores pessoas físicas não são guardados."""

    __tablename__ = "campanha_resumo"

    candidatura_id: Mapped[int] = mapped_column(
        ForeignKey("candidatura.id", ondelete="CASCADE"), primary_key=True
    )
    receitas_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    receitas_por_origem: Mapped[dict] = mapped_column(JSON)
    despesas_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    despesas_por_tipo: Mapped[dict] = mapped_column(JSON)
    numero_doadores: Mapped[int]
