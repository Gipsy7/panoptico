from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Cpi(Base):
    """Uma CPI (Câmara ou Senado) ou CPMI (Congresso) criada desde 2019, como a casa a
    registra: nome, objeto, datas, situação e, quando há, o link do relatório final."""

    __tablename__ = "cpi"
    __table_args__ = (UniqueConstraint("casa", "id_externo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    casa: Mapped[str] = mapped_column(String(12))  # camara | senado | congresso
    id_externo: Mapped[str] = mapped_column(String(20))  # órgão (Câmara) ou colegiado (Senado)
    tipo: Mapped[str] = mapped_column(String(5))  # CPI | CPMI
    sigla: Mapped[str | None] = mapped_column(String(60))
    nome: Mapped[str] = mapped_column(String(300))
    objeto: Mapped[str | None] = mapped_column(Text)  # finalidade, no texto da casa
    data_criacao: Mapped[date | None] = mapped_column(Date)
    data_instalacao: Mapped[date | None] = mapped_column(Date)
    # Câmara: fim do órgão. Senado/Congresso: último "prazo final" registrado, que pode ser
    # anterior ao encerramento de fato.
    data_fim: Mapped[date | None] = mapped_column(Date)
    situacao: Mapped[str | None] = mapped_column(String(80))
    relatorio_url: Mapped[str | None] = mapped_column(Text)
    relatorio_rotulo: Mapped[str | None] = mapped_column(String(200))
    fonte_url: Mapped[str | None] = mapped_column(Text)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class CpiParticipacao(Base):
    """Pessoa em uma CPI/CPMI, pelo id oficial do parlamentar na Câmara ou no Senado, com o
    cargo na comissão. A ligação à `pessoa` só existe quando o vínculo é forte."""

    __tablename__ = "cpi_participacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    cpi_id: Mapped[int] = mapped_column(ForeignKey("cpi.id", ondelete="CASCADE"), index=True)
    casa_parlamentar: Mapped[str] = mapped_column(String(10))  # camara | senado
    id_parlamentar: Mapped[str] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(200))
    partido: Mapped[str | None] = mapped_column(String(30))
    uf: Mapped[str | None] = mapped_column(String(2))
    cargo: Mapped[str] = mapped_column(String(30))  # Presidente | Vice-presidente | Relator |
    # Titular | Suplente
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    pessoa_id: Mapped[int | None] = mapped_column(
        ForeignKey("pessoa.id", ondelete="SET NULL"), index=True
    )
    regra: Mapped[str | None] = mapped_column(String(30))  # origem | nome_parlamentar


class CpiIndiciamentoSugestao(Base):
    """SUGESTÃO extraída do relatório final de uma CPI: nome citado na seção de
    indiciamentos. Nada aqui é publicável: nome em texto nunca é vínculo, e pedido de
    indiciamento não é acusação formal. `revisado` nasce falso e só uma pessoa o muda."""

    __tablename__ = "cpi_indiciamento_sugestao"
    __table_args__ = (UniqueConstraint("cpi_id", "nome_citado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cpi_id: Mapped[int] = mapped_column(ForeignKey("cpi.id", ondelete="CASCADE"), index=True)
    nome_citado: Mapped[str] = mapped_column(String(200))
    pessoa_juridica: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    trecho: Mapped[str] = mapped_column(Text)  # até 600 caracteres, como no relatório
    pagina: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)
    revisado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
