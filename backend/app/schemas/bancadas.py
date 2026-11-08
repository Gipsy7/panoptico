from datetime import datetime

from pydantic import BaseModel


class ItemBancada(BaseModel):
    partido: str
    n: int


class Bancada(BaseModel):
    itens: list[ItemBancada]
    total: int
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
    origem: str  # "assembleia" | "camara" | "senado" | "tse"


class BancadasEstado(BaseModel):
    uf: str
    assembleia: Bancada
    camara_uf: Bancada
    senado_uf: Bancada


class ComposicaoCongresso(BaseModel):
    casa: str
    hoje: list[ItemBancada]
    a_partir_2027: list[ItemBancada] | None
    total: int
    total_2027: int | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
    fonte_2027_nome: str | None
    fonte_2027_url: str | None
    atualizado_2027_em: datetime | None


class CadeirasPartido(BaseModel):
    partido: str
    camara: int
    senado: int
    prefeitos: int
    vereadores: int
    sigla_contas: str | None


class FonteCadeiras(BaseModel):
    nome: str
    url: str
    atualizado_em: datetime | None


class CadeirasPorPartido(BaseModel):
    itens: list[CadeirasPartido]
    total_camara: int
    total_senado: int
    ano_municipal: int | None
    fontes: list[FonteCadeiras]
