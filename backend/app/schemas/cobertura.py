from pydantic import BaseModel


class PedidoRef(BaseModel):
    arquivo: str
    orgao: str
    data: str | None = None
    url: str


class SecaoCobertura(BaseModel):
    secao: str
    situacao: str
    motivo: str
    fonte: str
    pedidos: list[PedidoRef]


class CasaCobertura(BaseModel):
    casa: str
    cargo: str
    secoes: list[SecaoCobertura]


class ContagemCobertura(BaseModel):
    sim: int
    parcial: int
    bloqueado: int
    pedido: int
    sem_fonte: int
    total: int


class CoberturaResposta(BaseModel):
    ufs: list[str]
    uf: str | None
    nacional: ContagemCobertura
    resumo_uf: ContagemCobertura | None
    casas: list[CasaCobertura]
    fonte_nome: str
    fonte_url: str
    atualizado_em: str
