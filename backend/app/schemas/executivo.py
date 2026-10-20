"""Respostas do Executivo (presidente, governador, prefeito e vices): contas do estado, painel
de resumo e agenda (docs/DECISOES.md, 19/10/2026, "Executivo com conteúdo")."""

from datetime import date, datetime, time

from pydantic import BaseModel

from app.schemas import AreaDespesa, ContasAnterior


class ContasEstadoResposta(BaseModel):
    uf: str
    ano: int
    populacao: int | None
    receita_total: float | None
    despesa_paga: float | None
    receita_por_habitante: float | None
    despesa_por_habitante: float | None
    media_estados_receita_por_habitante: float | None
    media_estados_despesa_por_habitante: float | None
    estados_na_media: int
    estados_sem_dado: int  # dos 27 (26 estados + DF), quantos ficaram fora da média
    estados_sem_dado_receita: int
    media_estados_descricao: str
    assembleia: float | None
    por_area: list[AreaDespesa]
    anterior: ContasAnterior | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class EnteExecutivo(BaseModel):
    tipo: str  # uniao | estado | municipio
    nome: str
    uf: str | None
    municipio_ibge: str | None


class BlocoPainel(BaseModel):
    """Um bloco do painel: `disponivel` falso diz por que não há o dado (nunca some em
    silêncio). `dados` varia por bloco; `rota` aponta para a rota completa."""

    disponivel: bool
    motivo: str | None = None
    dados: dict | None = None
    rota: str | None = None
    fonte_nome: str | None = None
    fonte_url: str | None = None
    atualizado_em: datetime | None = None


class PainelExecutivo(BaseModel):
    candidatura_id: int
    cargo: str
    titular: bool  # falso para vice
    nome_urna: str
    ano_eleicao: int
    ente: EnteExecutivo
    pessoa_id: int | None  # pessoa pública ligada por vínculo forte (para as rotas /pessoas)
    contas: BlocoPainel
    emendas: BlocoPainel
    contratos: BlocoPainel
    agenda: BlocoPainel
    viagens_cartao: BlocoPainel
    medidas_provisorias: BlocoPainel


class AgendaParticipantePublico(BaseModel):
    nome: str
    cargo: str | None
    orgao: str | None


class AgendaItem(BaseModel):
    tipo: str
    rotulo: str
    id_registro: int
    cargo: str | None
    orgao: str | None
    data_inicio: date | None
    data_fim: date | None
    hora_inicio: time | None
    hora_fim: time | None
    forma: str | None
    assunto: str | None
    local: str | None
    origem: str | None
    destino: str | None
    detalhes: str | None
    participantes_publicos: list[AgendaParticipantePublico]
    n_participantes_publicos: int
    entidades_privadas: list[str]
    n_participantes_privados: int
    url: str


class AgendaResposta(BaseModel):
    candidatura_id: int
    pessoa_id: int | None
    total: int
    pagina: int
    por_pagina: int
    itens: list[AgendaItem]
    nota: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
