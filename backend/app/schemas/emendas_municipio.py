"""Campos acrescentados à resposta de `/municipios/{ibge}/emendas` (18/10/2026).

Os campos antigos (`EmendasMunicipioResposta`) continuam com o mesmo sentido: emendas
individuais (com finalidade definida e transferências especiais) **pagas**. Os novos trazem
os outros tipos, o período coberto, os autores sem mandato atual, o previsto nos planos das
transferências especiais e os convênios, sempre separados do pago.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas import EmendaOutroAutor, EmendasMunicipioResposta


class EmendaTipo(BaseModel):
    tipo: str  # individual | especial | bancada | comissao | relator
    rotulo: str
    rotulo_oficial: str
    total: float
    pagamentos: int


class EmendaPeriodo(BaseModel):
    inicio: int | None
    fim: int | None


class EmendaOutroAutorDetalhe(EmendaOutroAutor):
    parlamentar_id: int | None = None
    pessoa_id: int | None = None
    com_mandato_atual: bool = False


class EmendaColegiado(BaseModel):
    autor_nome: str
    tipo: str
    rotulo: str
    total: float


class EmendaPrevistaItem(BaseModel):
    identificador: str
    emenda_codigo: str
    ano: int
    autor_nome: str | None
    parlamentar_id: int | None
    com_mandato_atual: bool
    beneficiario: str | None
    situacao: str | None
    valor: float
    fonte_url: str


class EmendasPrevistas(BaseModel):
    planos: int
    valor_planos: float
    planos_com_pagamento: int
    valor_planos_com_pagamento: float
    planos_sem_pagamento: int
    valor_sem_pagamento: float
    sem_pagamento: list[EmendaPrevistaItem]
    descricao: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class EmendaConvenioItem(BaseModel):
    identificador: str
    emendas: list[str]
    autores: list[str]
    beneficiario: str | None
    situacao: str | None
    valor_total: float
    valor_liberado: float


class EmendasConvenios(BaseModel):
    quantidade: int
    valor_total: float
    valor_liberado: float
    itens: list[EmendaConvenioItem]
    descricao: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class EmendasMunicipioCompleta(EmendasMunicipioResposta):
    periodo: EmendaPeriodo
    tipos: list[EmendaTipo]
    total_geral: float
    por_habitante_geral: float | None = None
    media_uf_por_habitante_geral: float | None = None
    outros_autores: list[EmendaOutroAutorDetalhe]
    numero_outros_autores: int
    autores_com_mandato: int
    autores_sem_mandato: int
    colegiados: list[EmendaColegiado]
    previsto: EmendasPrevistas | None
    convenios: EmendasConvenios | None
    sem_codigo_descricao: str
