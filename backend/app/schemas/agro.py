from datetime import datetime

from pydantic import BaseModel


class AgroProduto(BaseModel):
    produto: str
    valor: float
    percentual: float | None


class AgroRebanho(BaseModel):
    item: str
    cabecas: int


class AgroPecuariaResumo(BaseModel):
    ano: int
    rebanhos: list[AgroRebanho]
    valor_origem_animal: float | None
    produtos: list[AgroProduto]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class AgroMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    ano: int | None
    valor_total: float | None
    uf_valor_total: float | None
    produtos: list[AgroProduto]
    outros_produtos: int
    pecuaria: AgroPecuariaResumo | None = None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
