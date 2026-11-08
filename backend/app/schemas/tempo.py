from pydantic import BaseModel


class PontoAno(BaseModel):
    ano: int
    valor: float


class Comparacao(BaseModel):
    rotulo: str
    pontos: list[PontoAno]


class SerieTempo(BaseModel):
    id: str
    tema: str
    rotulo: str
    unidade: str
    responsavel: str
    decimais: int
    pontos: list[PontoAno]
    comparacoes: list[Comparacao]
    fonte_nome: str
    nota: str | None


class Gestao(BaseModel):
    inicio: int
    fim: int
    nome: str
    partido: str


class LinhaDoTempo(BaseModel):
    codigo: str
    uf: str
    ano_inicial: int | None
    ano_final: int | None
    reais_de: int | None
    series: list[SerieTempo]
    gestoes: dict[str, list[Gestao]]
