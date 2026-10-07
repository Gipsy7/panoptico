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


class ParlamentarDetalhe(ParlamentarResumo):
    nome_civil: str | None
    email: str | None
    telefone: str | None
    pagina_url: str | None
    em_exercicio: bool
    em_exercicio_desde: date | None
    fonte_url: str
    atualizado_em: datetime


class Localizacao(BaseModel):
    cep: str | None
    uf: str
    estado: str
    municipio: str | None


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
