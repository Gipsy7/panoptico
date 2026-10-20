from datetime import date, time

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgendaCompromisso(Base):
    """Um registro da agenda pública (e-Agendas, CGU) de uma pessoa da base que é agente
    público federal (ministro, vice-presidente que foi ministro...): reunião, evento, audiência,
    viagem ou presente/hospitalidade. Só entram pessoas ligadas por CPF parcial + nome.

    Coleta mínima (docs/DECISOES.md, "Executivo com conteúdo"): sem CPF; participantes que são
    agentes públicos com nome, cargo e órgão; participantes privados só como a entidade que
    representam (o nome da pessoa física não é guardado)."""

    __tablename__ = "agenda_compromisso"
    __table_args__ = (
        UniqueConstraint("pessoa_id", "tipo", "id_registro"),
        Index("ix_agenda_compromisso_pessoa_data", "pessoa_id", "data_inicio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="CASCADE"))
    # reuniao | evento | audiencia | audiencia_publica | viagem | presente
    tipo: Mapped[str] = mapped_column(String(20))
    id_registro: Mapped[int] = mapped_column(Integer)  # "ID do registro" no e-Agendas
    cargo: Mapped[str | None] = mapped_column(String(200))
    orgao: Mapped[str | None] = mapped_column(String(200))
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    hora_inicio: Mapped[time | None] = mapped_column(Time)
    hora_fim: Mapped[time | None] = mapped_column(Time)
    forma: Mapped[str | None] = mapped_column(String(20))  # Presencial | Virtual
    assunto: Mapped[str | None] = mapped_column(Text)
    local: Mapped[str | None] = mapped_column(String(200))
    origem: Mapped[str | None] = mapped_column(String(120))  # viagem
    destino: Mapped[str | None] = mapped_column(String(120))  # viagem
    detalhes: Mapped[str | None] = mapped_column(Text)  # viagem/presente: ofertante, item, valor
    # [{"nome", "cargo", "orgao"}], só agentes públicos com CPF mascarado na fonte
    participantes_publicos: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    n_participantes_publicos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # entidades representadas pelos participantes privados (sem o nome da pessoa)
    entidades_privadas: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    n_participantes_privados: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    publicado_em: Mapped[date | None] = mapped_column(Date)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
