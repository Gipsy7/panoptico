from datetime import date, datetime

from pydantic import BaseModel


class ObraSituacao(BaseModel):
    situacao: str
    obras: int
    valor_previsto: float


class ObraItem(BaseModel):
    id_unico: str
    nome: str
    situacao: str | None
    tipo: str | None
    valor_previsto: float | None
    percentual_execucao: float | None
    data_inicial_prevista: date | None
    data_final_prevista: date | None
    executor: str | None
    responsavel: str | None
    url: str


class ObrasMunicipio(BaseModel):
    municipio_ibge: str
    total: int
    valor_previsto: float
    por_situacao: list[ObraSituacao]
    itens: list[ObraItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class ObrasUf(BaseModel):
    uf: str
    total: int
    por_situacao: list[ObraSituacao]


class ObrasPorUf(BaseModel):
    ufs: list[ObrasUf]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
