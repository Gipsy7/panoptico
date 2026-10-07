from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Municipio(Base):
    """Municípios do IBGE. `nome_chave` é o nome sem acentos, em maiúsculas."""

    __tablename__ = "municipio"

    ibge: Mapped[str] = mapped_column(String(7), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    uf: Mapped[str] = mapped_column(String(2), index=True)
    nome_chave: Mapped[str] = mapped_column(String(100))
