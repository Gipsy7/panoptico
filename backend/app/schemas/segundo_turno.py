"""Respostas do comparador do 2º turno (arquivo à parte para não disputar o __init__)."""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas import BemItem, Localizacao, ValorNomeado


class BensAnteriores(BaseModel):
    ano: int
    cargo: str
    total: float | None


class BensDoCandidato(BaseModel):
    ano: int
    total: float
    quantidade: int
    maiores: list[BemItem]
    anterior: BensAnteriores | None
    fonte_url: str


class CampanhaDoCandidato(BaseModel):
    receitas_total: float
    despesas_total: float
    receitas_por_origem: list[ValorNomeado]
    numero_doadores: int
    fonte_url: str


class ViceDoCandidato(BaseModel):
    id: int
    nome_urna: str
    partido: str | None
    foto: bool


class CargoAnterior(BaseModel):
    ano: int
    cargo: str
    unidade: str
    partido: str | None
    situacao: str | None
    eleito: bool


class RegistroDoCandidato(BaseModel):
    data: date | None
    tipo: str
    descricao: str
    orgao: str | None
    situacao: str | None
    fonte_url: str | None


class CandidatoSegundoTurno(BaseModel):
    id: int
    nome_urna: str
    numero: str | None
    partido: str | None
    foto: bool
    foto_url: str | None
    vice: ViceDoCandidato | None
    votos_1turno: int | None
    votos_2turno: int | None
    eleito: bool | None
    bens: BensDoCandidato | None
    campanha: CampanhaDoCandidato | None
    carreira: list[CargoAnterior] | None
    sancoes: list[RegistroDoCandidato] | None
    pessoa_id: int | None
    perfil: str


class DisputaSegundoTurno(BaseModel):
    chave: str
    cargo: str
    unidade: str
    uf: str | None
    candidatos: list[CandidatoSegundoTurno]
    faltam: int
    decidida: bool


class GovernadorEleito(BaseModel):
    id: int
    nome_urna: str
    partido: str | None
    numero: str | None


class SegundoTurnoResposta(BaseModel):
    localizacao: Localizacao
    ano_eleicao: int | None
    data_segundo_turno: date | None
    em_andamento: bool
    disputas: list[DisputaSegundoTurno]
    governador_eleito_1turno: GovernadorEleito | None
    propostas_url: str
    fonte_nome: str
    fonte_url: str
    contas_url: str
    atualizado_em: datetime | None
    sancoes_fonte_nome: str
    sancoes_fonte_url: str
    sancoes_atualizado_em: datetime | None


class AgendaSegundoTurno(BaseModel):
    ano_eleicao: int | None
    data_segundo_turno: date | None
    em_andamento: bool
    presidente: bool
    ufs_governador: list[str]
