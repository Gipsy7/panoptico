"""Avisos de erro, direito de resposta e correções públicas (docs/DECISOES.md, 2026-11-07,
Frente 7). Sem IP nem user-agent. O contato de quem avisou fica numa tabela à parte
(`sugestao_contato`), fora do backup e apagada em 180 dias; nenhuma rota de leitura o expõe."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Sugestao(Base):
    """Aviso de erro (tipo "erro") ou resposta de quem é citado (tipo "resposta").

    status: "nova" (na fila), "aceita" (erro conferido), "recusada" ou "publicada" (resposta
    no perfil). Só a resposta publicada aparece no site."""

    __tablename__ = "sugestao"
    __table_args__ = (Index("ix_sugestao_perfil", "perfil_tipo", "perfil_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))
    categoria: Mapped[str | None] = mapped_column(String(20))
    texto: Mapped[str] = mapped_column(Text)
    pagina: Mapped[str] = mapped_column(String(300))
    secao: Mapped[str | None] = mapped_column(String(120))
    perfil_tipo: Mapped[str | None] = mapped_column(String(30))
    perfil_id: Mapped[str | None] = mapped_column(String(40))
    confirmacao: Mapped[str | None] = mapped_column(String(20))
    protocolo: Mapped[str] = mapped_column(String(12), unique=True)
    status: Mapped[str] = mapped_column(String(10), default="nova", server_default="nova")
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revisada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    publicada_em: Mapped[date | None] = mapped_column(Date)
    nota_revisao: Mapped[str | None] = mapped_column(Text)


class SugestaoContato(Base):
    """E-mail ou telefone opcional de quem avisou, só para responder. Fora do backup
    (deploy/vps/backup.sh) e apagado em 180 dias ou quando a sugestão é fechada."""

    __tablename__ = "sugestao_contato"

    sugestao_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sugestao.id", ondelete="CASCADE"), primary_key=True
    )
    contato: Mapped[str] = mapped_column(String(200))
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Correcao(Base):
    """Correção feita no site a partir de um aviso conferido com a fonte oficial. Pública,
    sem nada de quem avisou."""

    __tablename__ = "correcao"
    __table_args__ = (Index("ix_correcao_perfil", "perfil_tipo", "perfil_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    dado: Mapped[str] = mapped_column(String(200))
    antes: Mapped[str] = mapped_column(Text)
    depois: Mapped[str] = mapped_column(Text)
    motivo: Mapped[str] = mapped_column(Text)
    fonte: Mapped[str] = mapped_column(String(500))
    perfil_tipo: Mapped[str | None] = mapped_column(String(30))
    perfil_id: Mapped[str | None] = mapped_column(String(40))
    sugestao_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sugestao.id", ondelete="SET NULL")
    )
