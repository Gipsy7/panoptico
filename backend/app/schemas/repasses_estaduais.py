"""Resposta de `/municipios/{ibge}/repasses-estaduais`."""

from datetime import datetime

from pydantic import BaseModel


class TipoRepasseEstadual(BaseModel):
    chave: str
    rotulo: str
    termo_oficial: str
    explicacao: str
    por_lei: bool
    valor: float
    percentual: float
    por_habitante: float | None
    media_uf_por_habitante: float | None


class RepasseEstadualAnterior(BaseModel):
    ano: int
    total: float


class RepassesEstaduaisResposta(BaseModel):
    disponivel: bool
    motivo: str | None
    uf: str
    ano: int | None
    populacao: int | None
    total: float | None
    por_habitante: float | None
    media_uf_por_habitante: float | None
    municipios_na_media: int
    municipios_uf: int
    media_uf_descricao: str
    parte_por_lei: float | None
    percentual_por_lei: float | None
    fundeb: float | None
    tipos: list[TipoRepasseEstadual]
    anterior: RepasseEstadualAnterior | None
    anos_sem_contas: list[int]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
