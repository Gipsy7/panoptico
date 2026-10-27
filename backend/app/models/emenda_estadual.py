from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmendaEstadual(Base):
    """Emenda parlamentar ao orçamento de um **estado** (esfera estadual, à parte das federais
    de `emenda_pagamento`). Uma fonte por UF (ingestion/emendas_estaduais/registro.py); a
    linha é o que a fonte publica: proposta de transferência (SC), indicação (MG), emenda ×
    instrumento (ES), emenda × empenho (PE) ou emenda (BA, AC, AL, SE). `proposta` é a chave
    da linha na fonte, única na UF.

    A mesma emenda pode ter mais de uma linha: o valor previsto (`valor_previsto`) se repete
    nessas linhas e só pode ser somado uma vez por emenda (`codigo`); o pago e o empenhado são
    de cada linha e se somam."""

    __tablename__ = "emenda_estadual"
    __table_args__ = (
        UniqueConstraint("uf", "proposta"),
        Index("ix_emenda_estadual_municipio", "municipio_ibge", "ano"),
        Index("ix_emenda_estadual_uf_autor", "uf", "autor_chave"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uf: Mapped[str] = mapped_column(String(2))
    ano: Mapped[int] = mapped_column(SmallInteger)  # ano da emenda (Lei Orçamentária)
    codigo: Mapped[str] = mapped_column(String(60))  # "2024EP002132"
    proposta: Mapped[str] = mapped_column(String(60))  # chave da linha na fonte (única na UF)
    transferencia: Mapped[str | None] = mapped_column(String(60))  # "2024TR002516"
    tipo: Mapped[str] = mapped_column(String(12))  # individual | bancada
    autor_nome: Mapped[str] = mapped_column(String(200))
    autor_chave: Mapped[str] = mapped_column(String(200))  # comum.chave_nome do autor
    # Autor ligado a `pessoa` só por nome idêntico e único entre os deputados estaduais da
    # mesma Casa (eleitos pelo TSE ou no cargo hoje); nome parecido não liga. Bancadas: nulo.
    pessoa_id: Mapped[int | None] = mapped_column(
        ForeignKey("pessoa.id", ondelete="SET NULL"), index=True
    )
    municipio_ibge: Mapped[str | None] = mapped_column(ForeignKey("municipio.ibge"))
    municipio_nome: Mapped[str] = mapped_column(String(100))  # como veio da fonte
    # Pessoa física: sem nome nem CPF (só a categoria). Hoje a fonte só traz CNPJ.
    favorecido_nome: Mapped[str | None] = mapped_column(String(300))
    favorecido_cnpj: Mapped[str | None] = mapped_column(String(14))
    favorecido_natureza: Mapped[str | None] = mapped_column(String(80))
    orgao: Mapped[str | None] = mapped_column(String(200))  # concedente (área)
    instrumento: Mapped[str | None] = mapped_column(String(40))
    objeto: Mapped[str | None] = mapped_column(Text)
    situacao_proposta: Mapped[str | None] = mapped_column(String(60))
    situacao_transferencia: Mapped[str | None] = mapped_column(String(40))
    valor_previsto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    valor_empenhado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    valor_pago: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fonte: Mapped[str] = mapped_column(String(40))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
