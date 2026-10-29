from datetime import date

from sqlalchemy import (
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


class AtoPresidencial(Base):
    """Medida provisória editada ou veto aposto pelo Presidente da República, como o Congresso
    Nacional registra (API de processos do Senado, `/processo?sigla=MPV|VET`).

    Guardamos o mandato de 2023 em diante (docs/DECISOES.md, "Medidas provisórias e vetos do
    Presidente"). `situacao` é o texto literal da fonte; `decisao` é o código dela
    (PERDA_EFICACIA, MANTIDA_MATE, REJEITADO_PLENARIO...), vazio enquanto não houve decisão.
    """

    __tablename__ = "ato_presidencial"
    __table_args__ = (
        UniqueConstraint("tipo", "id_externo", name="uq_ato_presidencial_tipo_id_externo"),
        Index("ix_ato_presidencial_tipo_data", "tipo", "data"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))  # mpv | veto
    id_externo: Mapped[str] = mapped_column(String(20))  # codigoMateria no Congresso
    identificacao: Mapped[str] = mapped_column(String(30))  # "MPV 1287/2025", "VET 8/2024"
    numero: Mapped[int]
    ano: Mapped[int] = mapped_column(SmallInteger)
    ementa: Mapped[str] = mapped_column(Text)
    apelido: Mapped[str | None] = mapped_column(Text)  # MPV: nome popular, quando a fonte dá
    data: Mapped[date] = mapped_column(Date)  # edição da MP; chegada do veto ao Congresso
    data_decisao: Mapped[date | None] = mapped_column(Date)
    situacao: Mapped[str | None] = mapped_column(String(200))  # literal da fonte (só MPV)
    decisao: Mapped[str | None] = mapped_column(String(40))  # siglaTipoDeliberacao
    tramitando: Mapped[bool] = mapped_column(Boolean)
    veto_total: Mapped[bool | None] = mapped_column(Boolean)  # só veto
    norma_gerada: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
