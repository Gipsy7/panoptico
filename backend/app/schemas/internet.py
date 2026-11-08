from datetime import datetime

from pydantic import BaseModel


class InternetMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    ano: int | None
    mes: int | None
    acessos: int | None
    por_100_moradores: float | None
    uf_por_100_moradores: float | None
    brasil_por_100_moradores: float | None
    percentual_fibra: float | None
    percentual_rapida: float | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
