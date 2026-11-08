from datetime import datetime

from pydantic import BaseModel


class SaneamentoValores(BaseModel):
    agua_rede: float | None
    esgoto_rede: float | None
    lixo_coletado: float | None


class SaneamentoMunicipio(BaseModel):
    municipio_ibge: str
    uf: str
    ano: int | None
    cidade: SaneamentoValores
    estado: SaneamentoValores
    brasil: SaneamentoValores
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
