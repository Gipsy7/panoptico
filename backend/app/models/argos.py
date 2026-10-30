"""Registros do chat Argos (docs/DECISOES.md, 2026-10-30). Só o que o dono decidiu guardar:
texto já limpo (sem CEP, CPF, telefone, e-mail, URL nem número longo), o dia e o assunto.
Sem IP, sem user-agent, sem id de sessão, sem hora exata. Nada daqui vai para a API pública de
leitura nem para a exportação aberta."""

from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosFraseNaoEntendida(Base):
    __tablename__ = "argos_frase_nao_entendida"

    id: Mapped[int] = mapped_column(primary_key=True)
    texto: Mapped[str] = mapped_column(String(300))
    dia: Mapped[date] = mapped_column(Date, index=True)


class ArgosAvaliacao(Base):
    __tablename__ = "argos_avaliacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    util: Mapped[bool] = mapped_column(Boolean)
    assunto: Mapped[str] = mapped_column(String(40))
    dia: Mapped[date] = mapped_column(Date, index=True)


class ArgosConversa(Base):
    """Conversa guardada com o consentimento de quem avaliou "não ajudou"."""

    __tablename__ = "argos_conversa"

    id: Mapped[int] = mapped_column(primary_key=True)
    # [{"autor": "cidadao" | "argos", "texto": "..."}], até 30 itens de até 500 caracteres.
    mensagens: Mapped[list] = mapped_column(JSONB)
    dia: Mapped[date] = mapped_column(Date, index=True)
