"""Respostas da ficha do fornecedor e das emendas dos mais votados (14/11/2026)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class Bloco(BaseModel):
    recorte: str
    fonte_nome: str
    atualizado_em: datetime | None


class GabineteAno(BaseModel):
    ano: int
    valor: float
    gabinetes: int
    lancamentos: int


class GabineteMaior(BaseModel):
    parlamentar_id: int
    nome: str
    casa: Literal["camara", "senado"]
    partido: str | None
    uf: str
    valor: float


class Gabinetes(Bloco):
    por_ano: list[GabineteAno]
    ano_da_lista: int | None
    maiores: list[GabineteMaior]
    limite_da_lista: int


class PrefeituraAno(BaseModel):
    ano: int
    valor: float
    municipios: int


class PrefeituraMaior(BaseModel):
    ibge: str
    municipio: str
    uf: str
    orgao: str
    valor: float


class Prefeituras(Bloco):
    por_ano: list[PrefeituraAno]
    ano_da_lista: int | None
    maiores: list[PrefeituraMaior]
    limite_da_lista: int


class PncpAno(BaseModel):
    ano: int
    valor: float
    contratos: int
    municipios: int


class Pncp(Bloco):
    por_ano: list[PncpAno]


class EmendaAno(BaseModel):
    ano: int
    valor: float
    autores: int


class Convenios(BaseModel):
    quantidade: int
    valor_repassado: float


class Emendas(Bloco):
    pagas_por_ano: list[EmendaAno]
    convenios: Convenios


class Sancao(BaseModel):
    cadastro: str
    categoria: str
    abrangencia: str | None
    orgao: str | None
    inicio: date | None
    fim: date | None
    processo: str | None


class Sancoes(Bloco):
    itens: list[Sancao]
    fonte_url: str


class FichaFornecedor(BaseModel):
    cnpj: str
    nome: str | None
    nome_omitido: bool
    nome_fantasia: str | None
    uf: str | None
    situacao: str | None
    cadastro_referencia: str | None
    gabinetes: Gabinetes
    prefeituras: Prefeituras
    pncp: Pncp
    emendas: Emendas
    sancoes: Sancoes


class MunicipioCurto(BaseModel):
    ibge: str
    nome: str
    uf: str


class MaisVotadoComEmendas(BaseModel):
    posicao: int
    parlamentar_id: int
    nome: str
    partido: str | None
    uf: str
    votos: int
    emendas_pagas: float


class EmendasDosMaisVotados(BaseModel):
    municipio: MunicipioCurto
    ano_eleicao: int
    itens: list[MaisVotadoComEmendas]
    fora_por_nao_estar_em_exercicio: int
    emendas_dos_listados: float
    emendas_individuais_da_cidade: float
    emendas_de: int | None
    emendas_ate: int | None
    recorte: str
    votos_fonte_nome: str
    emendas_fonte_nome: str
    emendas_fonte_url: str
    atualizado_em: datetime | None
