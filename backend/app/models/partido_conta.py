from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PartidoContaSoma(Base):
    """Soma da prestação de contas anual de um partido (TSE), por esfera, UF, fonte do
    recurso e categoria. Guarda só totais: nada de doador, fornecedor ou CPF.

    `natureza` separa o que é dinheiro que entra ou sai do partido do que só muda de mãos
    dentro dele: sem isso, uma transferência do diretório nacional para o estadual aparece
    como despesa de um e receita do outro, e os totais contam o mesmo real duas vezes."""

    __tablename__ = "partido_conta_soma"
    __table_args__ = (
        UniqueConstraint(
            "ano", "tipo", "partido", "esfera", "uf", "fonte_recurso", "natureza", "categoria"
        ),
        Index("ix_partido_conta_soma_ano_partido", "ano", "partido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int]
    tipo: Mapped[str] = mapped_column(String(10))  # receita | despesa
    partido: Mapped[str] = mapped_column(String(30))
    esfera: Mapped[str] = mapped_column(String(20))  # Nacional, Estadual, Distrital, Municipal...
    uf: Mapped[str] = mapped_column(String(2), default="", server_default="")
    fonte_recurso: Mapped[str] = mapped_column(String(60))
    # receita: cota_tse | transferencia_partidaria | recurso_candidato | outra
    # despesa: gasto | transferencia_diretorio | transferencia_candidato | transferencia_outra
    natureza: Mapped[str] = mapped_column(String(30))
    categoria: Mapped[str] = mapped_column(String(200))
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    lancamentos: Mapped[int] = mapped_column(Integer)


class PartidoCotaMensal(Base):
    """Cotas do Fundo Partidário e do FEFC que o diretório nacional recebeu, mês a mês."""

    __tablename__ = "partido_cota_mensal"
    __table_args__ = (UniqueConstraint("ano", "mes", "partido", "fundo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int]  # exercício da prestação de contas
    mes: Mapped[date] = mapped_column(Date)  # primeiro dia do mês do recebimento
    partido: Mapped[str] = mapped_column(String(30))
    fundo: Mapped[str] = mapped_column(String(30))  # Fundo Partidário | FEFC
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class PartidoDespesaVinculada(Base):
    """Despesa de partido paga a um fornecedor que já aparece nos nossos dados: empresa
    sancionada ou sócia de alguém que acompanhamos (por CNPJ) ou pessoa que acompanhamos
    (por CPF). Coleta mínima: as demais linhas de despesa não são guardadas. O CPF nunca
    é gravado; a pessoa vem de `pessoa_id`."""

    __tablename__ = "partido_despesa_vinculada"
    __table_args__ = (Index("ix_partido_despesa_vinculada_ano_partido", "ano", "partido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int]
    partido: Mapped[str] = mapped_column(String(30))
    esfera: Mapped[str] = mapped_column(String(20))
    uf: Mapped[str] = mapped_column(String(2), default="", server_default="")
    municipio: Mapped[str | None] = mapped_column(String(120))
    sq_despesa: Mapped[str | None] = mapped_column(String(20))  # id da linha no arquivo do TSE
    fornecedor_cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    fornecedor_nome: Mapped[str | None] = mapped_column(String(300))  # só de empresas
    pessoa_id: Mapped[int | None] = mapped_column(
        ForeignKey("pessoa.id", ondelete="CASCADE"), index=True
    )
    motivo: Mapped[str] = mapped_column(String(60))  # sancao_empresa, socio_pessoa, pessoa
    categoria: Mapped[str] = mapped_column(String(200))
    fonte_recurso: Mapped[str] = mapped_column(String(60))
    natureza: Mapped[str] = mapped_column(String(30))
    data: Mapped[date | None] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class PartidoFefcFp(Base):
    """Distribuição do FEFC e do Fundo Partidário a candidaturas por gênero e por cor ou raça
    (arquivos fefc_fp do TSE), somada por eleição, partido e esfera.

    `valor_partido` (só FEFC) é o total do partido e se repete em cada linha dele: não some
    entre linhas, tome um valor por partido."""

    __tablename__ = "partido_fefc_fp"
    __table_args__ = (UniqueConstraint("ano", "fundo", "partido", "esfera", "genero", "cor_raca"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int]  # ano da eleição
    fundo: Mapped[str] = mapped_column(String(10))  # FEFC | FP
    partido: Mapped[str] = mapped_column(String(30))
    esfera: Mapped[str] = mapped_column(String(20))
    genero: Mapped[str] = mapped_column(String(20))
    cor_raca: Mapped[str] = mapped_column(String(20), default="", server_default="")  # "" = geral
    candidatos: Mapped[int]
    valor_recebido: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    valor_minimo_cota: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    valor_partido: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
