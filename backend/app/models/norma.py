from datetime import date

from sqlalchemy import Date, ForeignKey, Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Norma(Base):
    """Lei ordinária, lei complementar ou emenda constitucional federal, desde 1985, como o
    Senado Federal registra na base de legislação (`/dadosabertos/legislacao/lista`).

    `tipo`: LEI | LCP | EMC. `data` é a data da norma (a da assinatura, a que vai no nome: "Lei
    nº 14.133, de 1º de abril de 2021"). `data_publicacao` é a do Diário Oficial quando a Câmara
    a registra no despacho "Transformado na Lei..." (vazia nas demais). `url` é o texto oficial
    em normas.leg.br (URN do LexML). Ver docs/DECISOES.md, "Projetos que viraram lei".
    """

    __tablename__ = "norma"
    __table_args__ = (
        UniqueConstraint("id_externo", name="uq_norma_id_externo"),
        UniqueConstraint("tipo", "numero", "ano", name="uq_norma_tipo_numero_ano"),
        Index("ix_norma_ano_tipo", "ano", "tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    id_externo: Mapped[str] = mapped_column(String(20))  # código da norma no Senado
    tipo: Mapped[str] = mapped_column(String(10))
    numero: Mapped[int]
    ano: Mapped[int] = mapped_column(SmallInteger)
    data: Mapped[date] = mapped_column(Date)
    data_publicacao: Mapped[date | None] = mapped_column(Date)
    ementa: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class NormaProposicao(Base):
    """Projeto que virou a norma. `casa` + `proposicao_id_externo` é a mesma chave de
    `proposicao` (id da Câmara ou codigoMateria do Senado); a proposição pode não estar na tabela
    `proposicao` (projeto antigo). `identificacao` é como a Casa numera ("PLS 559/2013").
    `origem`: "senado" (processo do Senado com a norma gerada), "numero" (mesmo número na Câmara,
    numeração única desde 2019) ou "camara" (despacho "Transformado na Lei..." da Câmara)."""

    __tablename__ = "norma_proposicao"
    __table_args__ = (
        UniqueConstraint(
            "norma_id", "casa", "proposicao_id_externo", name="uq_norma_proposicao_norma_casa_id"
        ),
        Index("ix_norma_proposicao_casa_id", "casa", "proposicao_id_externo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    norma_id: Mapped[int] = mapped_column(ForeignKey("norma.id", ondelete="CASCADE"), index=True)
    casa: Mapped[str] = mapped_column(String(10))
    proposicao_id_externo: Mapped[str] = mapped_column(String(30))
    identificacao: Mapped[str | None] = mapped_column(String(60))
    origem: Mapped[str] = mapped_column(String(10))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
