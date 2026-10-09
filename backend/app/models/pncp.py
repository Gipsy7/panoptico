from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PncpSoma(Base):
    """Contratos do PNCP somados por dia de publicação × órgão × município × fornecedor × tipo
    de contrato (coleta mínima: o detalhe fica a um link da fonte). Alienações (`receita`)
    não entram. Empenhos ficam separados pelo tipo. Pessoa física e fornecedor estrangeiro
    entram sem identificador (`fornecedor_cnpj` vazio), nunca com CPF. A chave tem o dia
    porque o valor global muda com aditivos: reler um dia troca só as linhas dele."""

    __tablename__ = "pncp_soma"
    __table_args__ = (Index("ix_pncp_soma_fornecedor_cnpj", "fornecedor_cnpj"),)

    dia: Mapped[date] = mapped_column(Date, primary_key=True)  # data de publicação no PNCP
    orgao_cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    municipio_ibge: Mapped[str] = mapped_column(String(7), primary_key=True)  # vazio se sem
    tipo_pessoa: Mapped[str] = mapped_column(String(2), primary_key=True)  # PJ, PF, PE
    fornecedor_cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)  # vazio se não PJ
    tipo_contrato: Mapped[str] = mapped_column(String(60), primary_key=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    valor_global: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class PncpContrato(Base):
    """Contrato inteiro do PNCP, só quando o fornecedor (CNPJ) está no conjunto-alvo: sócios
    que acompanhamos (socio_pessoa) ou empresa sancionada (sancao_empresa)."""

    __tablename__ = "pncp_contrato"
    __table_args__ = (Index("ix_pncp_contrato_orgao_cnpj", "orgao_cnpj"),)

    numero_controle: Mapped[str] = mapped_column(String(40), primary_key=True)
    orgao_cnpj: Mapped[str] = mapped_column(String(14))
    orgao_nome: Mapped[str | None] = mapped_column(String(300))
    esfera: Mapped[str | None] = mapped_column(String(1))
    uf: Mapped[str | None] = mapped_column(String(2))
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    municipio_nome: Mapped[str | None] = mapped_column(String(120))
    fornecedor_cnpj: Mapped[str] = mapped_column(String(14), index=True)
    fornecedor_nome: Mapped[str | None] = mapped_column(String(300))  # sem CPF (MEI)
    tipo_contrato: Mapped[str] = mapped_column(String(60))
    categoria: Mapped[str | None] = mapped_column(String(60))
    receita: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    objeto: Mapped[str | None] = mapped_column(Text)
    valor_inicial: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    valor_global: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    valor_acumulado: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    data_assinatura: Mapped[date | None] = mapped_column(Date)
    vigencia_inicio: Mapped[date | None] = mapped_column(Date)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)
    publicado_em: Mapped[date] = mapped_column(Date)
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime)
    compra_pncp: Mapped[str | None] = mapped_column(String(40))
    processo: Mapped[str | None] = mapped_column(String(100))


class PncpOrgao(Base):
    """Nome e esfera dos órgãos que aparecem em pncp_soma (para exibir o CNPJ com nome)."""

    __tablename__ = "pncp_orgao"

    cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    nome: Mapped[str] = mapped_column(String(300))
    esfera: Mapped[str | None] = mapped_column(String(1))  # F, E, M, N
    poder: Mapped[str | None] = mapped_column(String(1))  # E, L, J, N
    uf: Mapped[str | None] = mapped_column(String(2))


class PncpDia(Base):
    """Cursor e conferência: um dia de publicação já lido, com o total que a API informou
    (`totalRegistros`) e quantos contratos foram lidos. O maior dia é o ponto de partida da
    próxima coleta."""

    __tablename__ = "pncp_dia"

    dia: Mapped[date] = mapped_column(Date, primary_key=True)
    total_api: Mapped[int] = mapped_column(Integer)
    lidos: Mapped[int] = mapped_column(Integer)
    receitas: Mapped[int] = mapped_column(Integer)  # alienações, fora das somas
    empenhos: Mapped[int] = mapped_column(Integer)
    pessoas_fisicas: Mapped[int] = mapped_column(Integer)  # somadas sem identificador
    linhas_alvo: Mapped[int] = mapped_column(Integer)  # contratos guardados inteiros
    lido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
