from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PautaItem(Base):
    """Matéria na pauta do Plenário da Câmara ou do Senado, na janela de hoje a +14 dias.
    A janela inteira é recarregada a cada carga (docs/DECISOES.md, 2026-10-21)."""

    __tablename__ = "pauta_item"
    __table_args__ = (Index("ix_pauta_item_casa_data", "casa", "data"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    data: Mapped[date] = mapped_column(Date)
    # Id da sessão na fonte (evento da Câmara, CodigoSessao do Senado).
    sessao: Mapped[str] = mapped_column(String(30))
    ordem: Mapped[int | None] = mapped_column(SmallInteger)
    # Rótulo ("PL 123/2025") e id da matéria na fonte (o mesmo de votacao.proposicao_id_externo).
    proposicao: Mapped[str | None] = mapped_column(String(60))
    proposicao_id_externo: Mapped[str | None] = mapped_column(String(30), index=True)
    ementa: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class Tramitacao(Base):
    """Uma linha do caminho de uma proposição, como a Casa publica. `proposicao_id_externo`
    é o id da proposição na Câmara ou o codigoMateria do Senado (o mesmo de `votacao`).
    A proposição pode não estar na tabela `proposicao` (matéria antiga votada)."""

    __tablename__ = "tramitacao"
    __table_args__ = (
        Index("ix_tramitacao_casa_proposicao_ordem", "casa", "proposicao_id_externo", "ordem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(10))
    proposicao_id_externo: Mapped[str] = mapped_column(String(30))
    ordem: Mapped[int] = mapped_column(SmallInteger)
    data: Mapped[datetime] = mapped_column(DateTime)
    orgao: Mapped[str | None] = mapped_column(String(60))
    # Tipo do ato como a Câmara classifica ("Votação (Plenário)"); o Senado não classifica.
    tipo: Mapped[str | None] = mapped_column(String(200))
    # Texto oficial: despacho (Câmara) ou informe legislativo (Senado).
    descricao: Mapped[str] = mapped_column(Text)
    situacao: Mapped[str | None] = mapped_column(String(200))
    # Marca da fonte na hora da busca (Câmara: data e sequência do último status; Senado:
    # dataUltimaAtualizacao). A carga só rebusca a proposição quando a marca muda.
    fonte_marca: Mapped[str | None] = mapped_column(String(40))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
