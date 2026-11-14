from datetime import datetime

from pydantic import BaseModel


class FonteResultado(BaseModel):
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None = None


class MunicipioRef(BaseModel):
    ibge: str
    nome: str
    uf: str


class TotaisResultado(BaseModel):
    aptos: int
    comparecimento: int
    abstencoes: int
    brancos: int
    nulos: int
    validos: int
    pct_comparecimento: float | None = None
    pct_brancos: float | None = None
    pct_nulos: float | None = None
    exterior_incluido: bool = False


class CandidatoResultado(BaseModel):
    nome_urna: str
    numero: str | None = None
    partido: str | None = None
    votos: int
    pct: float | None = None
    situacao: str | None = None
    eleito: bool
    candidatura_id: int | None = None


class EleitoAnterior(BaseModel):
    nome_urna: str
    partido: str | None = None
    votos: int


class EleicaoAnterior(BaseModel):
    ano: int
    turno: int
    eleitos: list[EleitoAnterior]


class ResultadoEleicao(FonteResultado):
    ano: int
    cargo: str
    turno: int
    turnos: list[int]
    abrangencia: str
    uf: str | None = None
    municipio: MunicipioRef | None = None
    proporcional: bool
    totais: TotaisResultado | None = None
    candidatos: list[CandidatoResultado]
    total_candidatos: int
    anteriores: list[EleicaoAnterior]
    destaque_candidatura_id: int | None = None


class EleicaoDisponivel(BaseModel):
    ano: int
    cargo: str
    turnos: list[int]


class MaisVotadoItem(BaseModel):
    posicao: int
    # Perfil do parlamentar, quando a candidatura é de alguém em exercício hoje (ligação do
    # cadastro do TSE com o da Casa, não por nome). Acrescentado em 14/11/2026.
    parlamentar_id: int | None = None
    nome_urna: str
    partido: str | None = None
    votos: int
    pct: float | None = None
    situacao: str | None = None
    eleito: bool
    candidatura_id: int | None = None


class MaisVotadosCargo(BaseModel):
    cargo: str
    nominais: int | None = None
    votos_em_eleitos: int | None = None
    pct_em_eleitos: float | None = None
    itens: list[MaisVotadoItem]


class MaisVotados(FonteResultado):
    ano: int
    municipio: MunicipioRef | None = None
    cargos: list[MaisVotadosCargo]


class PopulacaoRef(BaseModel):
    valor: int
    ano: int
    origem: str | None = None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None = None


class Eleitores(FonteResultado):
    municipio: MunicipioRef | None = None
    ano: int
    cargo_referencia: str
    eleitores: int
    votaram: int
    pct_votaram: float | None = None
    populacao: PopulacaoRef | None = None
    eleitores_por_100_moradores: int | None = None


class PessoaNoCargo(BaseModel):
    nome: str
    partido: str | None = None
    candidatura_id: int | None = None


class MandatoAnterior(BaseModel):
    ano: int
    inicio: int
    fim: int
    pessoas: list[PessoaNoCargo]


class Antecessores(FonteResultado):
    cargo: str
    uf: str | None = None
    municipio: MunicipioRef | None = None
    mandatos: list[MandatoAnterior]
