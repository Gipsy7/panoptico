"""Alertas de operação já enviados ao dono (app/services/alertas.py). Serve para não repetir o
mesmo aviso na mesma janela e para o painel privado mostrar o histórico. Sem dado pessoal."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AlertaEnviado(Base):
    __tablename__ = "alerta_enviado"
    __table_args__ = (UniqueConstraint("chave", "janela", name="uq_alerta_enviado_chave_janela"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # fluxo | ingestao | saude | disco
    chave: Mapped[str] = mapped_column(String(40))
    # Um aviso por chave e janela: o dia ("2026-11-13") ou a hora ("2026-11-13T14").
    janela: Mapped[str] = mapped_column(String(13))
    assunto: Mapped[str] = mapped_column(String(200))
    texto: Mapped[str] = mapped_column(Text)
    enviado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
