from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ObraFederal(Base):
    """Obra ou projeto de investimento com recurso federal, do Obrasgov.br (API pública do
    Ministério da Gestão): situação, datas, valor previsto e o percentual de execução física
    mais recente. O município vem de `obra_federal_municipio` (a obra pode ter mais de um)."""

    __tablename__ = "obra_federal"
    __table_args__ = (Index("ix_obra_federal_uf_situacao", "uf", "situacao"),)

    id_unico: Mapped[str] = mapped_column(String(20), primary_key=True)
    nome: Mapped[str] = mapped_column(String(400))
    situacao: Mapped[str | None] = mapped_column(String(40))
    natureza: Mapped[str | None] = mapped_column(String(60))
    especie: Mapped[str | None] = mapped_column(String(60))
    tipo: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    data_inicial_prevista: Mapped[date | None] = mapped_column(Date)
    data_final_prevista: Mapped[date | None] = mapped_column(Date)
    data_inicial_efetiva: Mapped[date | None] = mapped_column(Date)
    data_final_efetiva: Mapped[date | None] = mapped_column(Date)
    data_cadastro: Mapped[date | None] = mapped_column(Date)
    valor_previsto: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    valor_previsto_federal: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    responsavel: Mapped[str | None] = mapped_column(String(300))
    executor: Mapped[str | None] = mapped_column(String(300))
    percentual_execucao: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    execucao_atualizada_em: Mapped[date | None] = mapped_column(Date)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class ObraFederalMunicipio(Base):
    """Em que município fica cada obra (geometria do Obrasgov, com o código do IBGE)."""

    __tablename__ = "obra_federal_municipio"
    __table_args__ = (Index("ix_obra_federal_municipio_ibge", "municipio_ibge"),)

    obra_id: Mapped[str] = mapped_column(
        ForeignKey("obra_federal.id_unico", ondelete="CASCADE"), primary_key=True
    )
    municipio_ibge: Mapped[str] = mapped_column(String(7), primary_key=True)


class IdebResultado(Base):
    """Nota do IDEB (INEP) de uma edição, por município, estado ou Brasil, etapa e rede."""

    __tablename__ = "ideb_resultado"

    abrangencia: Mapped[str] = mapped_column(String(10), primary_key=True)  # municipio|uf|brasil
    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)  # IBGE, UF ou "BR"
    etapa: Mapped[str] = mapped_column(String(10), primary_key=True)  # iniciais|finais|medio
    rede: Mapped[str] = mapped_column(String(10), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(3, 1))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class PibIbge(Base):
    """PIB dos Municípios (IBGE, SIDRA 5938), em mil reais a preços correntes: código de 1
    dígito = Brasil, 2 = UF, 7 = município (o mesmo de `populacao_ibge`). As atividades ficam
    vazias nos anos em que o IBGE só publicou o total."""

    __tablename__ = "pib_ibge"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    pib: Mapped[Decimal] = mapped_column(Numeric(16, 0))
    vab_total: Mapped[Decimal | None] = mapped_column(Numeric(16, 0))
    vab_agropecuaria: Mapped[Decimal | None] = mapped_column(Numeric(16, 0))
    vab_industria: Mapped[Decimal | None] = mapped_column(Numeric(16, 0))
    vab_servicos: Mapped[Decimal | None] = mapped_column(Numeric(16, 0))
    vab_administracao: Mapped[Decimal | None] = mapped_column(Numeric(16, 0))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class AgroLavoura(Base):
    """Valor da produção das lavouras (IBGE, PAM, tabela 5457) por produto, em mil reais, no
    último ano publicado: código de 1 dígito = Brasil, 2 = UF, 7 = município. "Total" é a soma
    de todos os produtos, como o IBGE publica."""

    __tablename__ = "agro_lavoura"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    produto: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 0))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class AgroPecuaria(Base):
    """Pecuária (IBGE, PPM) no último ano: `rebanho` em cabeças (tabela 3939) e `produto` de
    origem animal em mil reais (tabela 74). Código de 1 dígito = Brasil, 2 = UF, 7 = município."""

    __tablename__ = "agro_pecuaria"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    categoria: Mapped[str] = mapped_column(String(10), primary_key=True)  # rebanho | produto
    item: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(16, 0))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class EmpregoIbge(Base):
    """Cadastro Central de Empresas (IBGE, tabela 9509): empresas, pessoas ocupadas,
    assalariados e salário médio mensal (em reais e em salários mínimos), por ano. Código de 1
    dígito = Brasil, 2 = UF, 7 = município. Não inclui o trabalho informal."""

    __tablename__ = "emprego_ibge"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    empresas: Mapped[Decimal | None] = mapped_column(Numeric(12, 0))
    pessoal_ocupado: Mapped[Decimal] = mapped_column(Numeric(12, 0))
    assalariados: Mapped[Decimal | None] = mapped_column(Numeric(12, 0))
    salario_medio: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salario_medio_sm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class EmpregoSetor(Base):
    """Pessoas ocupadas por seção de atividade (CNAE 2.0, tabela 9510) no último ano."""

    __tablename__ = "emprego_setor"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    secao: Mapped[str] = mapped_column(String(1), primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    pessoal_ocupado: Mapped[Decimal] = mapped_column(Numeric(12, 0))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class InternetFixa(Base):
    """Banda larga fixa (Anatel) no mês mais recente: acessos por município, os de fibra
    (FTTH/FTTB) e os de mais de 34 Mbps. A conta por 100 moradores é feita na API."""

    __tablename__ = "internet_fixa"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    mes: Mapped[int] = mapped_column(SmallInteger)
    acessos: Mapped[int] = mapped_column(Integer)
    acessos_fibra: Mapped[int] = mapped_column(Integer)
    acessos_rapidos: Mapped[int] = mapped_column(Integer)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class SaneamentoCenso(Base):
    """Saneamento no Censo 2022 (IBGE), em % dos domicílios: água da rede geral como forma
    principal, esgoto na rede (ou fossa ligada a ela) e lixo coletado. Código de 1 dígito =
    Brasil, 2 = UF, 7 = município."""

    __tablename__ = "saneamento_censo"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    agua_rede: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    esgoto_rede: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    lixo_coletado: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
