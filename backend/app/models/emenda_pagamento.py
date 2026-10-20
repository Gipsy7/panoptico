from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmendaPagamento(Base):
    """Valor de emenda (individual, Pix, bancada, comissão ou relator) recebido por
    prefeitura, fundo municipal ou entidade sem fins lucrativos de um município (Portal da
    Transparência, por favorecido). É o valor **pago**, desde o primeiro ano do arquivo."""

    __tablename__ = "emenda_pagamento"
    __table_args__ = (
        Index("ix_emenda_pagamento_municipio", "municipio_ibge", "ano_emenda"),
        Index("ix_emenda_pagamento_parlamentar", "parlamentar_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    emenda_codigo: Mapped[str] = mapped_column(String(20))
    ano_emenda: Mapped[int] = mapped_column(SmallInteger)
    ano_mes: Mapped[int] = mapped_column(Integer)
    autor_codigo: Mapped[str] = mapped_column(String(20))
    autor_nome: Mapped[str] = mapped_column(String(200))
    parlamentar_id: Mapped[int | None] = mapped_column(
        ForeignKey("parlamentar.id", ondelete="SET NULL")
    )
    # Autor ligado a `pessoa` por vínculo forte (nome exato e único entre os eleitos), para
    # quem não está mais no cargo. Colegiados (bancada, comissão, relator) ficam nulos.
    pessoa_id: Mapped[int | None] = mapped_column(ForeignKey("pessoa.id", ondelete="SET NULL"))
    # individual | especial | bancada | comissao | relator (nulo só em linhas anteriores à
    # migração 0047, até a próxima carga)
    tipo: Mapped[str | None] = mapped_column(String(12))
    favorecido: Mapped[str] = mapped_column(String(300))
    favorecido_codigo: Mapped[str] = mapped_column(String(20))
    natureza: Mapped[str] = mapped_column(String(100))
    grupo: Mapped[str] = mapped_column(String(20))  # "prefeitura" | "entidade"
    municipio_ibge: Mapped[str] = mapped_column(ForeignKey("municipio.ibge"))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class EmendaPagamentoSemCodigo(Base):
    """Pagamento do arquivo por favorecido da CGU com código da emenda "Sem informação"
    (20/10/2026). A fonte informa o tipo de emenda e o mês do pagamento, mas não o autor nem
    o ano da emenda: o autor fica como veio ("Sem informação" ou o marcador "-99 RELATOR
    GERAL") e nunca é ligado a parlamentar ou pessoa. Mesmos favorecidos de
    `emenda_pagamento` (prefeitura, fundos municipais e entidades sem fins lucrativos)."""

    __tablename__ = "emenda_pagamento_sem_codigo"
    __table_args__ = (Index("ix_emenda_pagamento_sem_codigo_municipio", "municipio_ibge"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ano_mes: Mapped[int] = mapped_column(Integer)
    # individual | especial | bancada | comissao | relator; nulo se a fonte não trouxer o tipo
    tipo: Mapped[str | None] = mapped_column(String(12))
    autor_codigo: Mapped[str] = mapped_column(String(20))
    autor_nome: Mapped[str] = mapped_column(String(200))
    favorecido: Mapped[str] = mapped_column(String(300))
    favorecido_codigo: Mapped[str] = mapped_column(String(20))
    natureza: Mapped[str] = mapped_column(String(100))
    grupo: Mapped[str] = mapped_column(String(20))
    municipio_ibge: Mapped[str] = mapped_column(ForeignKey("municipio.ibge"))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
