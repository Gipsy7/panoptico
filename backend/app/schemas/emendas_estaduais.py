"""Emendas estaduais (esfera estadual, nunca somadas às federais). Ver
app/services/emendas_estaduais.py."""

from datetime import datetime

from pydantic import BaseModel


class EmendaEstadualSomas(BaseModel):
    previsto: float
    empenhado: float
    pago: float
    emendas: int


class EmendaEstadualAno(EmendaEstadualSomas):
    ano: int


class EmendaEstadualAutor(EmendaEstadualSomas):
    autor_nome: str
    tipo: str  # individual | bancada
    pessoa_id: int | None
    mandato_id: int | None
    em_exercicio: bool


class EmendaEstadualFavorecido(EmendaEstadualSomas):
    nome: str
    cnpj: str | None


class EmendasEstaduaisMunicipio(BaseModel):
    uf: str
    casa: str
    total_previsto: float
    total_empenhado: float
    total_pago: float
    emendas: int
    por_autor: list[EmendaEstadualAutor]
    por_ano: list[EmendaEstadualAno]
    favorecidos: list[EmendaEstadualFavorecido]
    numero_favorecidos: int
    somado_ao_federal: bool
    descricao: str
    recorte: str
    termos: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class EmendaEstadualPeriodo(BaseModel):
    inicio: int | None
    fim: int | None


class EmendaEstadualMunicipioDestino(EmendaEstadualSomas):
    ibge: str | None
    nome: str


class EmendaEstadualItem(BaseModel):
    codigo: str
    ano: int
    municipio_ibge: str | None
    municipio_nome: str
    favorecido: str
    orgao: str | None
    objeto: str | None
    situacao: str | None
    previsto: float
    empenhado: float | None
    pago: float


class EmendasDeputadoEstadual(BaseModel):
    mandato_id: int
    nome: str
    uf: str
    casa: str
    periodo: EmendaEstadualPeriodo
    total_previsto: float
    total_empenhado: float
    total_pago: float
    emendas: int
    media_casa_pago: float | None
    deputados_na_media: int
    media_descricao: str
    por_ano: list[EmendaEstadualAno]
    por_municipio: list[EmendaEstadualMunicipioDestino]
    numero_municipios: int
    itens: list[EmendaEstadualItem]
    numero_itens: int
    descricao: str
    recorte: str
    termos: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
