from sqlalchemy import ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ResultadoCandidato(Base):
    """Votos de um candidato numa disputa, somados das zonas (votacao_candidato_munzona do TSE).

    `abrangencia`:
    - "disputa": o total na disputa inteira (o país para presidente, a UF para governador,
      senador e deputados, o município para prefeito e vereador). Todos os candidatos.
    - "municipio": o recorte de uma eleição geral num município. Presidente, governador e
      senador: todos os candidatos; deputados: só os 10 mais votados ali ("mais votados aqui").

    `uf` é "BR" na disputa de presidente. `municipio_ibge` é o município da disputa (eleição
    municipal) ou do recorte; vazio nas disputas estaduais e nacional. `situacao` é a do TSE no
    turno ("ELEITO", "ELEITO POR QP", "SUPLENTE"...). Ver docs/DECISOES.md, "Eleições completas".
    """

    __tablename__ = "resultado_candidato"
    __table_args__ = (
        Index(
            "ix_resultado_candidato_disputa",
            "ano",
            "cargo",
            "turno",
            "abrangencia",
            "uf",
            "municipio_ibge",
        ),
        Index("ix_resultado_candidato_sq", "ano", "sq_candidato"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    turno: Mapped[int] = mapped_column(SmallInteger)
    cargo: Mapped[str] = mapped_column(String(40))
    abrangencia: Mapped[str] = mapped_column(String(10))
    uf: Mapped[str] = mapped_column(String(2))
    municipio_ibge: Mapped[str | None] = mapped_column(String(7))
    sq_candidato: Mapped[str] = mapped_column(String(30))
    numero: Mapped[str | None] = mapped_column(String(10))
    nome_urna: Mapped[str] = mapped_column(String(120))
    partido: Mapped[str | None] = mapped_column(String(30))
    votos: Mapped[int] = mapped_column(Integer)
    situacao: Mapped[str | None] = mapped_column(String(40))
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))


class ResultadoTotais(Base):
    """Comparecimento e votos de um cargo num município e turno (detalhe_votacao_munzona do
    TSE, somado das zonas). O total da UF ou do país é a soma dos municípios.

    `validos` = nominais + legenda. `votos_em_eleitos` (só deputados, eleições gerais): votos
    dados ali a candidatos que se elegeram, para a frase "X% dos votos daqui foram para quem se
    elegeu"; o denominador é `nominais`."""

    __tablename__ = "resultado_totais"
    __table_args__ = (
        Index("ix_resultado_totais_mun", "ano", "cargo", "turno", "municipio_ibge", unique=True),
        Index("ix_resultado_totais_uf", "ano", "cargo", "turno", "uf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger)
    turno: Mapped[int] = mapped_column(SmallInteger)
    cargo: Mapped[str] = mapped_column(String(40))
    uf: Mapped[str] = mapped_column(String(2))
    municipio_ibge: Mapped[str] = mapped_column(String(7))
    aptos: Mapped[int] = mapped_column(Integer)
    comparecimento: Mapped[int] = mapped_column(Integer)
    abstencoes: Mapped[int] = mapped_column(Integer)
    brancos: Mapped[int] = mapped_column(Integer)
    nulos: Mapped[int] = mapped_column(Integer)
    validos: Mapped[int] = mapped_column(Integer)
    nominais: Mapped[int] = mapped_column(Integer)
    votos_em_eleitos: Mapped[int | None] = mapped_column(Integer)
    ingestao_id: Mapped[int | None] = mapped_column(ForeignKey("fonte_ingestao.id"))
