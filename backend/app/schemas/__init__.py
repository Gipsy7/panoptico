from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ParlamentarResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    casa: str
    nome_parlamentar: str
    partido: str | None
    uf: str
    foto_url: str | None


class Remuneracao(BaseModel):
    subsidio_mensal: float
    vigente_desde: date
    fonte_nome: str
    fonte_url: str


class ParlamentarDetalhe(ParlamentarResumo):
    nome_civil: str | None
    email: str | None
    telefone: str | None
    pagina_url: str | None
    em_exercicio: bool
    em_exercicio_desde: date | None
    fonte_url: str
    atualizado_em: datetime
    remuneracao: Remuneracao


class Localizacao(BaseModel):
    cep: str | None
    uf: str
    estado: str
    municipio: str | None
    codigo_ibge: str | None = None


class RepresentantesResposta(BaseModel):
    localizacao: Localizacao
    deputados: list[ParlamentarResumo]
    senadores: list[ParlamentarResumo]
    atualizado_em: datetime | None


class GastoCategoria(BaseModel):
    categoria: str
    total: float


class GastoMes(BaseModel):
    mes: int
    total: float


class DespesaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes: int
    categoria: str
    fornecedor: str | None
    valor: float
    data: date | None
    url_documento: str | None


class GastosResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    ultimo_mes: int | None
    total: float
    media_casa: float
    por_categoria: list[GastoCategoria]
    por_mes: list[GastoMes]
    maiores_despesas: list[DespesaItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class ProjetoTipo(BaseModel):
    sigla: str
    nome: str
    primeiro_autor: int
    coautor: int


class ProjetoItem(BaseModel):
    sigla_tipo: str
    numero: int
    ano: int
    ementa: str
    data_apresentacao: date
    situacao: str | None
    virou_lei: bool
    url: str
    primeiro_autor: bool


class ProjetosResposta(BaseModel):
    desde: date
    primeiro_autor: int
    coautor: int
    viraram_norma: int
    media_casa_primeiro_autor: float
    por_tipo: list[ProjetoTipo]
    recentes: list[ProjetoItem]
    viraram_norma_lista: list[ProjetoItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class Justificativa(BaseModel):
    motivo: str
    quantidade: int


class PresencaResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    periodo_inicio: date
    total_votacoes: int
    votou: int
    presente_sem_voto: int
    justificada: int
    nao_compareceu: int
    justificativas: list[Justificativa]
    percentual: float | None
    media_casa_percentual: float | None
    ausencia_detalhada: bool
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class MunicipioInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ibge: str
    nome: str
    uf: str


class EmendaAno(BaseModel):
    ano: int
    total: float


class EmendaParlamentar(BaseModel):
    parlamentar: ParlamentarResumo
    total: float
    do_estado: bool


class EmendaOutroAutor(BaseModel):
    autor_nome: str
    total: float


class EmendasMunicipioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    municipio: MunicipioInfo
    desde: int
    total: float
    total_prefeitura: float
    total_entidades: float
    por_ano: list[EmendaAno]
    parlamentares: list[EmendaParlamentar]
    outros_autores: list[EmendaOutroAutor]
    numero_autores: int
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class FonteItem(BaseModel):
    dado: str
    orgao: str
    url: str
    atualizado_em: datetime | None


class Criterio(BaseModel):
    id: str
    nome: str
    definicao: str


class ParlamentarNaLista(BaseModel):
    id: int
    casa: str
    nome_parlamentar: str
    partido: str | None
    uf: str
    foto_url: str | None
    gastos: float
    presenca_votou: int
    presenca_total: int
    presenca: float | None
    governo_iguais: int
    governo_total: int
    governo: float | None
    partido_iguais: int
    partido_total: int
    partido_pct: float | None
    projetos: int
    homenagens: int
    normas: int
    emendas: float


class ListaParlamentaresResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    ordenar: str
    ordem: str
    criterios: list[Criterio]
    medias: dict[str, dict[str, float | None]]
    partidos: list[str]
    total: int
    pagina: int
    por_pagina: int
    itens: list[ParlamentarNaLista]
    atualizado_em: datetime | None
