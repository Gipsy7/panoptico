from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProposicaoTema(Base):
    """Tema oficial de uma proposição, segundo a classificação da própria Casa.

    Sem chave estrangeira de propósito: cobre também proposições votadas de anos antigos,
    que não estão na tabela `proposicao` (lá só ficam as apresentadas desde 2023)."""

    __tablename__ = "proposicao_tema"

    casa: Mapped[str] = mapped_column(String(10), primary_key=True)
    proposicao_id_externo: Mapped[str] = mapped_column(String(30), primary_key=True)
    tema: Mapped[str] = mapped_column(String(100), primary_key=True)
