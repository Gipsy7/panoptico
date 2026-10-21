"""Respostas de projetos, votações locais e pauta (rotas em app/api/projetos.py)."""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.votacao import GrupoDiscursos, PorUf


class FonteBloco(BaseModel):
    """Fonte e data de um bloco da página."""

    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


# ---- Busca ----


class UltimaVotacao(BaseModel):
    data: date | None
    resultado: str | None
    sim: int | None
    nao: int | None
    descricao: str | None
    link: str


class ItemProjeto(BaseModel):
    tipo: str  # proposicao | votacao_local | projeto_local
    rotulo: str
    ementa: str | None
    esfera: str  # federal | estadual | municipal
    casa: str  # camara | senado | assembleia | camara_municipal
    uf: str | None
    municipio_ibge: str | None
    municipio: str | None
    situacao: str | None
    virou_lei: bool | None
    ultima_votacao: UltimaVotacao | None
    na_pauta: date | None
    ultima_movimentacao: date | None
    link: str


class BuscaProjetos(BaseModel):
    q: str | None
    total: int
    pagina: int
    por_pagina: int
    itens: list[ItemProjeto]
    fontes: list[FonteBloco]


# ---- Projeto federal ----


class AutorProjeto(BaseModel):
    parlamentar_id: int
    nome: str
    partido: str | None
    uf: str
    primeiro_autor: bool


class FichaProjeto(FonteBloco):
    temas: list[str]
    autores: list[AutorProjeto]
    autor_descricao: str | None
    situacao: str | None
    virou_lei: bool | None
    relator: str | None
    relator_parlamentar_id: int | None
    url_oficial: str | None
    origem: str | None  # legislatura | votada | None (só existe na tabela de votações)
    data_apresentacao: date | None


class PlacarContado(BaseModel):
    sim: int
    nao: int
    abstencao: int
    obstrucao: int
    outros: int


class PlacarPublicado(BaseModel):
    sim: int | None
    nao: int | None
    abstencao: int | None


class VotacaoDoProjeto(BaseModel):
    id_externo: str
    data: date
    descricao: str
    resultado: str | None
    secreta: bool
    placar_publicado: PlacarPublicado | None
    placar_contado: PlacarContado
    link: str


class BlocoVotacoes(FonteBloco):
    itens: list[VotacaoDoProjeto]
    aviso: str | None  # quando não há votação nominal


class PessoaQueVotou(BaseModel):
    parlamentar_id: int
    nome: str
    partido: str
    uf: str
    registro: str  # "Sim", "Não" ou o registro em linguagem simples


class QuantidadePorPartido(BaseModel):
    partido: str
    quantidade: int


class GrupoQuemVotou(BaseModel):
    chave: str  # sim | nao | outros
    rotulo: str
    quantidade: int
    partidos: list[QuantidadePorPartido]
    pessoas: list[PessoaQueVotou]


class BlocoQuemVotou(FonteBloco):
    votacao: VotacaoDoProjeto
    regra: str
    grupos: list[GrupoQuemVotou]
    por_uf: list[PorUf]


class DiaDeDiscursos(BaseModel):
    data: date
    votacao_id_externo: str | None
    total: int
    grupos: list[GrupoDiscursos]


class BlocoDiscursos(FonteBloco):
    dias: list[DiaDeDiscursos]
    aviso: str


class DiscursosDoDia(FonteBloco):
    quantidade_nao_atribuida: int
    itens: list[dict]
    aviso: str


class PassoDoCaminho(BaseModel):
    data: datetime
    orgao: str | None
    descricao: str
    etapa: str


class BlocoCaminho(FonteBloco):
    itens: list[PassoDoCaminho]


class ProximaPauta(BaseModel):
    data: date
    sessao: str
    url: str | None


class BlocoPauta(FonteBloco):
    proxima: ProximaPauta | None


class ProjetoDetalhe(BaseModel):
    casa: str
    id_externo: str
    rotulo: str
    sigla: str | None
    numero: int | None
    ano: int | None
    ementa: str | None
    ficha: FichaProjeto
    votacoes: BlocoVotacoes
    votacao_principal: BlocoQuemVotou | None
    discursos: BlocoDiscursos
    discursos_do_dia: DiscursosDoDia
    caminho: BlocoCaminho
    pauta: BlocoPauta


# ---- Local ----


class AutorLocal(BaseModel):
    mandato_id: int
    nome: str
    partido: str | None


class VotoDoLocal(BaseModel):
    mandato_id: int
    nome: str
    partido: str | None
    voto: str


class VotacaoLocalResumo(BaseModel):
    id: int
    data: date | None
    materia: str
    resultado: str | None
    sim: int
    nao: int
    abstencoes: int
    link: str


class ProjetoLocalDetalhe(FonteBloco):
    id: int
    rotulo: str
    tipo: str
    numero: int | None
    ano: int
    ementa: str
    data_apresentacao: date | None
    em_tramitacao: bool | None
    casa: str
    uf: str | None
    municipio_ibge: str | None
    municipio: str | None
    autor: AutorLocal | None
    votacoes: list[VotacaoLocalResumo]
    url_oficial: str
    sem_orientacao: bool
    sem_discursos: bool
    aviso: str


class VotacaoLocalDetalhe(FonteBloco):
    id: int
    casa: str
    uf: str
    municipio_ibge: str | None
    municipio: str | None
    data: date | None
    materia: str
    ementa: str | None
    resultado: str | None
    sim: int
    nao: int
    abstencoes: int
    votos: list[VotoDoLocal]
    projeto_local_id: int | None
    projeto_link: str | None
    url_oficial: str | None
    sem_orientacao: bool
    sem_discursos: bool
    aviso: str


# ---- Pauta ----


class ItemDePauta(BaseModel):
    casa: str
    data: date
    sessao: str
    ordem: int | None
    proposicao: str | None
    proposicao_id_externo: str | None
    ementa: str | None
    url_oficial: str | None
    link: str | None  # página do projeto aqui, quando existe


class Pauta(FonteBloco):
    casa: str | None
    dias: int
    itens: list[ItemDePauta]
    aviso: str | None
