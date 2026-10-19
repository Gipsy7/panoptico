from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Empresa(Base):
    """Cadastro de CNPJs que aparecem nos nossos dados (fornecedor, beneficiário, sancionada),
    da base aberta do CNPJ da Receita Federal. Só os CNPJs de interesse: coleta mínima. A razão
    social de MEI traz o CPF do titular: quando traz, `razao_social` fica vazia e
    `nome_omitido` é verdadeiro (nunca se guarda CPF)."""

    __tablename__ = "empresa"
    __table_args__ = (Index("ix_empresa_municipio", "municipio_ibge"),)

    cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    razao_social: Mapped[str | None] = mapped_column(String(300))
    nome_omitido: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    nome_fantasia: Mapped[str | None] = mapped_column(String(300))
    natureza_juridica: Mapped[str | None] = mapped_column(String(4))  # código (ex.: 1244)
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    uf: Mapped[str | None] = mapped_column(String(2))
    situacao: Mapped[str | None] = mapped_column(String(2))  # 02 ativa, 03 suspensa, 04 inapta...
    referencia: Mapped[str] = mapped_column(String(10))  # mês da base ("2026-10") ou "brasilapi"
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
