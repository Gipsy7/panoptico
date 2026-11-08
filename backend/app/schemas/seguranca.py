from datetime import datetime

from pydantic import BaseModel


class HomicidiosAno(BaseModel):
    ano: int
    homicidios: int
    por_100_mil: float | None


class HomicidiosLugar(BaseModel):
    serie: list[HomicidiosAno]
    media_3_anos_por_100_mil: float | None


class SegurancaMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    cidade: HomicidiosLugar
    estado: HomicidiosLugar
    brasil: HomicidiosLugar
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
