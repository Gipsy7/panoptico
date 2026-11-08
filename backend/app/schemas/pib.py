from datetime import datetime

from pydantic import BaseModel


class PibAno(BaseModel):
    ano: int
    pib: float
    por_habitante: float | None
    uf_por_habitante: float | None
    brasil_por_habitante: float | None


class PibSetor(BaseModel):
    setor: str
    valor: float
    percentual: float


class PibSetores(BaseModel):
    ano: int
    itens: list[PibSetor]


class PibMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    serie: list[PibAno]
    setores: PibSetores | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
