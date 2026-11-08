from datetime import datetime

from pydantic import BaseModel


class SaudeLugar(BaseModel):
    leitos: int
    leitos_sus: int
    leitos_por_mil: float | None
    leitos_complementares: int
    leitos_complementares_sus: int
    complementares_por_100_mil: float | None
    ubs: int
    ubs_por_10_mil: float | None
    hospitais: int


class SaudeMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    ano: int | None
    mes: int | None
    cidade: SaudeLugar | None
    estado: SaudeLugar | None
    brasil: SaudeLugar | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
