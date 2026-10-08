from datetime import date

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MandatoLocal(Base):
    """Vereador (câmara municipal) ou deputado estadual (assembleia) na legislatura atual,
    como a própria casa publica (SAPL do Interlegis): quem está no cargo hoje, titular ou
    suplente, com o partido atual. Ligado ao eleito do TSE pelo nome quando a
    correspondência é exata e única."""

    __tablename__ = "mandato_local"
    __table_args__ = (
        UniqueConstraint("municipio_ibge", "id_externo"),
        Index("ix_mandato_local_casa_uf", "casa", "uf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(12), default="camara", server_default="camara")
    uf: Mapped[str] = mapped_column(String(2))
    # Vazio nas assembleias (a casa é do estado inteiro).
    municipio_ibge: Mapped[str | None] = mapped_column(
        ForeignKey("municipio.ibge", ondelete="CASCADE"), index=True
    )
    id_externo: Mapped[str] = mapped_column(String(20))  # id do parlamentar no SAPL
    nome: Mapped[str] = mapped_column(String(200))
    nome_completo: Mapped[str | None] = mapped_column(String(200))
    partido: Mapped[str | None] = mapped_column(String(30))
    foto_url: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(60))
    titular: Mapped[bool] = mapped_column(Boolean, default=True)
    em_exercicio: Mapped[bool] = mapped_column(Boolean, default=True)
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    # Quantas proposições apresentou como autor no período guardado, por tipo
    # (requerimentos, indicações, moções...): só a contagem, sem guardar cada uma.
    proposicoes_por_tipo: Mapped[dict] = mapped_column(JSON, default=dict)
    candidatura_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidatura.id", ondelete="SET NULL")
    )
    sapl_url: Mapped[str] = mapped_column(Text)


class ProjetoLocal(Base):
    """Projeto de lei (e afins) de vereador, do SAPL: só os tipos que viram norma e só o
    período recente (ano atual e anterior)."""

    __tablename__ = "projeto_local"
    __table_args__ = (
        UniqueConstraint("mandato_id", "id_externo"),
        Index("ix_projeto_local_mandato", "mandato_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipio_ibge: Mapped[str | None] = mapped_column(
        ForeignKey("municipio.ibge", ondelete="CASCADE"), index=True
    )
    mandato_id: Mapped[int] = mapped_column(ForeignKey("mandato_local.id", ondelete="CASCADE"))
    id_externo: Mapped[str] = mapped_column(String(20))
    tipo: Mapped[str] = mapped_column(String(120))
    numero: Mapped[int | None]
    ano: Mapped[int] = mapped_column(SmallInteger)
    ementa: Mapped[str] = mapped_column(Text)
    data_apresentacao: Mapped[date | None] = mapped_column(Date)
    em_tramitacao: Mapped[bool | None]
    primeiro_autor: Mapped[bool] = mapped_column(Boolean, default=True)
    url: Mapped[str] = mapped_column(Text)
