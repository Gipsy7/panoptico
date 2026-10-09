from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Regras de ligação, da mais forte para a mais fraca (docs/DECISOES.md, "acervo local").
# Só as fortes, ou as revisadas à mão, são publicadas.
REGRAS_FORTES = {
    "origem", "cpf", "titulo", "cpf_parcial_nome", "nome_nascimento", "tse",
    # Nome parlamentar exato e único no cadastro da própria Câmara (atribuído por ela).
    "nome_parlamentar",
}  # fmt: skip


class Pessoa(Base):
    """Uma pessoa pública, a mesma em todas as fontes: o ponto único a que se ligam
    candidaturas, mandatos e, a partir da fase de Justiça e controle, processos, sanções e
    eventos. CPF e título servem só para ligar registros e nunca são exibidos."""

    __tablename__ = "pessoa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    chave_nome: Mapped[str] = mapped_column(String(200), index=True)  # comum.chave_nome
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    cpf: Mapped[str | None] = mapped_column(String(11), index=True)
    titulo: Mapped[str | None] = mapped_column(String(12), index=True)


class PessoaVinculo(Base):
    """Um registro de uma fonte ligado a uma pessoa, com a regra que fez a ligação.

    `fonte` + `id_externo` identificam o registro de forma estável entre recargas (não o id
    interno, que muda quando a carga apaga e reinsere): candidatura = "ano:sq_candidato",
    parlamentar = "casa:id", mandato_local = "casa:uf:município:id no SAPL"."""

    __tablename__ = "pessoa_vinculo"
    __table_args__ = (UniqueConstraint("fonte", "id_externo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="CASCADE"), index=True)
    fonte: Mapped[str] = mapped_column(String(40))
    id_externo: Mapped[str] = mapped_column(String(80))
    # origem | cpf | titulo | tse | cpf_parcial_nome | nome_nascimento (fortes)
    # nome_casa (média: só publicada se revisada)
    regra: Mapped[str] = mapped_column(String(30))
    revisado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Evento(Base):
    """Um fato datado da vida pública de uma pessoa (eleição, posse, processo aberto,
    decisão, sanção, cassação, nomeação...), com a fonte oficial. É a linha do tempo que
    as funcionalidades consomem num formato só, qualquer que seja a fonte."""

    __tablename__ = "evento"
    __table_args__ = (
        UniqueConstraint("fonte", "id_externo", "tipo"),
        Index("ix_evento_pessoa_data", "pessoa_id", "data"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="CASCADE"))
    # O registro da fonte que liga o fato à pessoa: o evento só é publicado se esse
    # vínculo for forte ou revisado.
    vinculo_id: Mapped[int | None] = mapped_column(
        ForeignKey("pessoa_vinculo.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[date | None] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(40))  # eleito, cassacao, sancao, processo...
    descricao: Mapped[str] = mapped_column(Text)  # factual, sem adjetivos
    orgao: Mapped[str | None] = mapped_column(String(120))
    numero_processo: Mapped[str | None] = mapped_column(String(40))
    situacao: Mapped[str | None] = mapped_column(String(80))
    fonte: Mapped[str] = mapped_column(String(50))
    id_externo: Mapped[str] = mapped_column(String(100))
    fonte_url: Mapped[str | None] = mapped_column(Text)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
    # Participação num caso (curadoria): o papel da pessoa segundo um documento oficial.
    caso_slug: Mapped[str | None] = mapped_column(
        ForeignKey("caso.slug", ondelete="CASCADE"), index=True
    )


class Processo(Base):
    """Situação de um processo judicial já citado num evento (cassação, sanção...), lida
    no DataJud do CNJ pelo número único. Processo sob sigilo fica só com o número."""

    __tablename__ = "processo"

    numero: Mapped[str] = mapped_column(String(25), primary_key=True)  # formato CNJ
    tribunal: Mapped[str | None] = mapped_column(String(12))
    classe: Mapped[str | None] = mapped_column(String(150))
    orgao_julgador: Mapped[str | None] = mapped_column(String(200))
    data_ajuizamento: Mapped[date | None] = mapped_column(Date)
    ultimo_andamento: Mapped[str | None] = mapped_column(String(200))
    data_ultimo_andamento: Mapped[date | None] = mapped_column(Date)
    sigiloso: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    encontrado: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    consultado_em: Mapped[date] = mapped_column(Date)


class Caso(Base):
    """Um caso (escândalo) montado só com documentos oficiais, por curadoria versionada
    em data/casos/<slug>/. Cada pessoa entra pelo papel que um documento lhe dá."""

    __tablename__ = "caso"

    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    periodo: Mapped[str | None] = mapped_column(String(40))
    resumo: Mapped[str] = mapped_column(Text)
    conferido_em: Mapped[date] = mapped_column(Date)


class CasoDocumento(Base):
    __tablename__ = "caso_documento"
    __table_args__ = (UniqueConstraint("caso_slug", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    caso_slug: Mapped[str] = mapped_column(ForeignKey("caso.slug", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(40))  # id do documento no CSV do caso
    tipo: Mapped[str] = mapped_column(String(40))  # processo, denuncia, acordao, relatorio_cpi...
    orgao: Mapped[str] = mapped_column(String(120))
    numero: Mapped[str | None] = mapped_column(String(60))
    data: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str] = mapped_column(Text)
    resumo: Mapped[str] = mapped_column(Text)


class SancaoEmpresa(Base):
    """Sanção da CGU (CEIS, CNEP) a uma empresa que aparece como fornecedor nos dados que
    já temos (coleta mínima: as demais não são guardadas). Serve aos cruzamentos de
    backend/analises/; a abrangência diz onde a sanção vale."""

    __tablename__ = "sancao_empresa"
    __table_args__ = (UniqueConstraint("cadastro", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cadastro: Mapped[str] = mapped_column(String(10))
    codigo: Mapped[str] = mapped_column(String(20))
    cnpj: Mapped[str] = mapped_column(String(14), index=True)
    nome: Mapped[str] = mapped_column(String(300))
    categoria: Mapped[str] = mapped_column(String(200))
    abrangencia: Mapped[str | None] = mapped_column(String(120))
    orgao: Mapped[str | None] = mapped_column(String(300))
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    processo: Mapped[str | None] = mapped_column(String(40))
