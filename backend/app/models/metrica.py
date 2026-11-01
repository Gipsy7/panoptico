"""Contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). Só totais por dia, aparelho e
categoria de origem: sem IP, sem user-agent, sem identificador de pessoa, navegador ou sessão e
sem hora. Nada daqui vai para a API pública de leitura nem para a exportação aberta."""

from datetime import date

from sqlalchemy import BigInteger, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetricaDiaria(Base):
    __tablename__ = "metrica_diaria"
    __table_args__ = (Index("ix_metrica_diaria_tipo_dia", "tipo", "dia"),)

    dia: Mapped[date] = mapped_column(Date, primary_key=True)
    # pagina | visita | entrada | ultima | recurso | busca | uf | cidade | perfil | partido | secao
    tipo: Mapped[str] = mapped_column(String(12), primary_key=True)
    chave: Mapped[str] = mapped_column(String(120), primary_key=True)
    aparelho: Mapped[str] = mapped_column(String(10), primary_key=True)  # celular | computador
    origem: Mapped[str] = mapped_column(String(12), primary_key=True)  # categoria, ver o serviço
    total: Mapped[int] = mapped_column(BigInteger, default=0)
