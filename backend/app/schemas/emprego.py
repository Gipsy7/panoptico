from datetime import datetime

from pydantic import BaseModel


class EmpregoAno(BaseModel):
    ano: int
    empresas: float | None
    pessoal_ocupado: float | None
    assalariados: float | None
    salario_medio: float | None
    salario_medio_sm: float | None
    uf_salario_medio: float | None
    brasil_salario_medio: float | None


class EmpregoSetorItem(BaseModel):
    secao: str
    nome: str
    pessoal_ocupado: float
    percentual: float | None


class EmpregoMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    serie: list[EmpregoAno]
    setores_ano: int | None
    setores: list[EmpregoSetorItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
