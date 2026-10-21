from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Discurso(Base):
    """Discurso em Plenário (Câmara ou Senado) de um dia em que houve votação nominal.

    Guarda só o sumário oficial e os links; nunca a transcrição. A ligação é ao projeto e ao
    dia, nunca a uma votação específica (docs/DECISOES.md, 2026-10-21)."""

    __tablename__ = "discurso"
    __table_args__ = (
        UniqueConstraint("casa", "id_externo", name="uq_discurso_casa_id_externo"),
        Index("ix_discurso_casa_proposicao_data", "casa", "proposicao_id_externo", "data"),
        Index("ix_discurso_casa_data", "casa", "data"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    # Senado: CodigoPronunciamento. Câmara: a fonte não tem id; chave estável
    # "<id do deputado>:<data e hora>:<ocorrência no mesmo instante>".
    id_externo: Mapped[str] = mapped_column(String(60))
    parlamentar_id: Mapped[int | None] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[date] = mapped_column(Date)
    data_hora: Mapped[datetime | None] = mapped_column(DateTime)
    # Senado: CodigoSessao (o mesmo da API de votações).
    sessao_id_externo: Mapped[str | None] = mapped_column(String(30))
    # Como a fonte publica: fase/sessão ("Ordem do Dia") e tipo ("DISCUSSÃO").
    fase: Mapped[str | None] = mapped_column(String(120))
    tipo: Mapped[str | None] = mapped_column(String(120))
    sumario: Mapped[str | None] = mapped_column(Text)
    url_texto: Mapped[str | None] = mapped_column(Text)
    url_video: Mapped[str | None] = mapped_column(Text)
    # Projeto votado no dia a que o discurso se refere (só com 1 ou 2 matérias citadas).
    proposicao_id_externo: Mapped[str | None] = mapped_column(String(30))
    materias_citadas: Mapped[int] = mapped_column(Integer, default=0)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
