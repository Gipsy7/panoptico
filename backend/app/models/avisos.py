"""Avisos por Web Push (docs/DECISOES.md, 2026-10-30).

`aviso_evento` guarda só fatos públicos e diz o que é novo: as cargas apagam e reinserem, e os
ids internos mudam, então a identidade do fato é a chave natural. `aviso_inscricao` e
`aviso_alvo` são os únicos dados de cidadão: endereço de envio e chaves do navegador, sem nome,
e-mail, telefone ou IP. Ficam fora da API de leitura, da exportação aberta e do backup.

Release e produção dividem o banco: toda consulta de inscrição filtra por `ambiente`.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AvisoEvento(Base):
    __tablename__ = "aviso_evento"
    __table_args__ = (
        UniqueConstraint(
            "alvo_tipo", "alvo_chave", "categoria", "chave_natural", name="uq_aviso_evento_chave"
        ),
        Index("ix_aviso_evento_detectado_em", "detectado_em"),
    )

    # BigInteger: ON CONFLICT DO NOTHING gasta um número da sequência a cada linha repetida.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alvo_tipo: Mapped[str] = mapped_column(String(12))  # parlamentar | projeto
    alvo_chave: Mapped[str] = mapped_column(String(45))  # casa:id_externo
    categoria: Mapped[str] = mapped_column(String(12))  # voto | tramitacao | evento
    chave_natural: Mapped[str] = mapped_column(String(200))
    titulo: Mapped[str] = mapped_column(String(300))
    caminho: Mapped[str] = mapped_column(String(120))  # relativo ao site
    fonte: Mapped[str] = mapped_column(String(120))  # nome do órgão, como a fonte publica
    data_fato: Mapped[date] = mapped_column(Date)
    detectado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AvisoInscricao(Base):
    __tablename__ = "aviso_inscricao"
    __table_args__ = (
        UniqueConstraint("ambiente", "endpoint", name="uq_aviso_inscricao_ambiente_endpoint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ambiente: Mapped[str] = mapped_column(String(20))
    endpoint: Mapped[str] = mapped_column(String(1000))
    p256dh: Mapped[str] = mapped_column(String(256))
    auth: Mapped[str] = mapped_column(String(64))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_sucesso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Até onde este aparelho recebeu. Nulo: acompanha o cursor do ambiente. Uma falha passageira
    # o fixa, e o aparelho recebe no dia seguinte o que perdeu, mesmo com o cursor à frente.
    ultimo_evento_id: Mapped[int | None] = mapped_column(BigInteger)


class AvisoAlvo(Base):
    __tablename__ = "aviso_alvo"
    __table_args__ = (
        UniqueConstraint("inscricao_id", "alvo_tipo", "alvo_chave", name="uq_aviso_alvo_chave"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inscricao_id: Mapped[int] = mapped_column(ForeignKey("aviso_inscricao.id", ondelete="CASCADE"))
    alvo_tipo: Mapped[str] = mapped_column(String(12))
    alvo_chave: Mapped[str] = mapped_column(String(45))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AvisoCursor(Base):
    """Último evento já resumido em cada ambiente. Sem linha, o ambiente ainda não foi semeado."""

    __tablename__ = "aviso_cursor"

    ambiente: Mapped[str] = mapped_column(String(20), primary_key=True)
    ultimo_evento_id: Mapped[int] = mapped_column(BigInteger)
