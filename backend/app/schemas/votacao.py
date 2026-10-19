"""Respostas do explicador de votação (GET /votacoes/{casa}/{id_externo})."""

from datetime import date, datetime

from pydantic import BaseModel


class PlacarVotacao(BaseModel):
    sim: int
    nao: int
    abstencao: int
    obstrucao: int


class PlacarOficial(BaseModel):
    sim: int | None
    nao: int | None
    abstencao: int | None


class RegistroContado(BaseModel):
    rotulo: str
    quantidade: int


class OrientacaoLideranca(BaseModel):
    bancada: str
    orientacao: str | None


class OrientacaoGrupo(BaseModel):
    bancada: str  # como a fonte publica ("Bl UniPpPsd...")
    tipo: str  # bloco | federacao | outra
    orientacao: str
    partidos: list[str]


class Seguiram(BaseModel):
    iguais: int
    total: int
    percentual: float | None


class PartidoNaVotacao(BaseModel):
    partido: str
    parlamentares: int
    sim: int
    nao: int
    abstencao: int
    obstrucao: int
    outros: int
    votos_efetivos: int
    orientacao: str | None
    orientacao_por: str | None  # bloco/federação de onde veio a orientação
    seguiram: int | None


class ParlamentarNaVotacao(BaseModel):
    parlamentar_id: int
    nome: str
    partido: str
    uf: str
    voto: str
    registro: str
    efetivo: bool


class VotacaoDetalhe(BaseModel):
    casa: str
    id_externo: str
    data: date
    descricao: str
    proposicao: str | None
    proposicao_ementa: str | None
    proposicao_url: str | None
    temas: list[str]
    secreta: bool
    resultado: str | None
    placar: PlacarVotacao
    outros_registros: list[RegistroContado]
    placar_oficial: PlacarOficial | None
    registros: int
    cadeiras: int
    liderancas: list[OrientacaoLideranca]
    outras_bancadas: list[OrientacaoGrupo]
    seguiram_governo: Seguiram
    seguiram_partido: Seguiram
    partidos: list[PartidoNaVotacao]
    parlamentares: list[ParlamentarNaVotacao]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
