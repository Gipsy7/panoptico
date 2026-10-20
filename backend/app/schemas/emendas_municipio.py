"""Campos acrescentados à resposta de `/municipios/{ibge}/emendas` (18/10/2026).

Os campos antigos (`EmendasMunicipioResposta`) continuam com o mesmo sentido: emendas
individuais (com finalidade definida e transferências especiais) **pagas**. Os novos trazem
os outros tipos, o período coberto, os autores sem mandato atual, o previsto nos planos das
transferências especiais e os convênios, sempre separados do pago.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas import EmendaOutroAutor, EmendasMunicipioResposta
from app.schemas.emendas_estaduais import EmendasEstaduaisMunicipio


class EmendaTipo(BaseModel):
    tipo: str  # individual | especial | bancada | comissao | relator
    rotulo: str
    rotulo_oficial: str
    total: float
    pagamentos: int
    # Parte de `total` que vem de pagamentos sem código de emenda na CGU (tipo informado pela
    # fonte, autor e ano não): também está em `sem_identificacao` (20/10/2026).
    sem_codigo_total: float = 0
    sem_codigo_pagamentos: int = 0


class EmendaSemIdentificacaoTipo(BaseModel):
    tipo: str | None  # nulo quando a fonte não traz o tipo
    rotulo: str
    rotulo_oficial: str | None
    total: float
    pagamentos: int


class EmendasSemIdentificacao(BaseModel):
    """Pagamentos com código da emenda "Sem informação" no arquivo da CGU: sem autor e sem
    ano da emenda. Estão somados em `total_geral` e no tipo correspondente de `tipos`, e
    nunca em autor algum."""

    total: float
    pagamentos: int
    primeiro_pagamento: int | None  # AAAAMM
    ultimo_pagamento: int | None
    por_tipo: list[EmendaSemIdentificacaoTipo]
    incluido_no_total_geral: bool = True
    descricao: str


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
    # 20/10/2026: pagamentos sem código de emenda, à vista (já somados em `total_geral`).
    sem_identificacao: EmendasSemIdentificacao | None = None
    # Esfera estadual (19/10/2026): à parte, nunca somada aos totais federais acima. Nulo
    # onde o estado não tem fonte de emendas estaduais.
    estaduais: EmendasEstaduaisMunicipio | None = None
