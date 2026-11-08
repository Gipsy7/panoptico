from pydantic import BaseModel


class CidadeParecida(BaseModel):
    ibge: str
    nome: str
    uf: str
    esta: bool
    populacao: int
    pib_por_morador: float | None
    pib_ano: int | None
    ideb: float | None
    ideb_ano: int | None
    salario_medio: float | None
    salario_ano: int | None


class CidadesParecidas(BaseModel):
    ano_populacao: int | None
    cidades: list[CidadeParecida]


class Vocacao(BaseModel):
    atividade: str
    percentual: float
    percentual_brasil: float
    razao: float | None


class Vocacoes(BaseModel):
    pib_ano: int | None
    pib: list[Vocacao]
    emprego_ano: int | None
    emprego: list[Vocacao]
