from datetime import datetime

from pydantic import BaseModel


class IdebPonto(BaseModel):
    ano: int
    valor: float


class IdebRede(BaseModel):
    rede: str
    serie: list[IdebPonto]
    uf: list[IdebPonto]
    brasil: list[IdebPonto]


class IdebEtapa(BaseModel):
    etapa: str
    rotulo: str
    redes: list[IdebRede]


class IdebMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    etapas: list[IdebEtapa]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
