from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Regras de ligação, da mais forte para a mais fraca (docs/DECISOES.md, "acervo local").
# Só as fortes, ou as revisadas à mão, são publicadas.
REGRAS_FORTES = {"origem", "cpf", "titulo", "cpf_parcial_nome", "nome_nascimento", "tse"}


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
