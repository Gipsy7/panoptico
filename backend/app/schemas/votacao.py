"""Respostas do explicador de votação (GET /votacoes/{casa}/{id_externo})."""

from datetime import date, datetime

from pydantic import BaseModel


class PlacarVotacao(BaseModel):
    sim: int
    nao: int
    abstencao: int
    obstrucao: int


class PlacarOficial(BaseModel):
    sim: int | None
    nao: int | None
    abstencao: int | None


class RegistroContado(BaseModel):
    rotulo: str
    quantidade: int


class OrientacaoLideranca(BaseModel):
    bancada: str
    orientacao: str | None


class OrientacaoGrupo(BaseModel):
    bancada: str  # como a fonte publica ("Bl UniPpPsd...")
    tipo: str  # bloco | federacao | outra
    orientacao: str
    partidos: list[str]


class Seguiram(BaseModel):
    iguais: int
    total: int
    percentual: float | None


class PartidoNaVotacao(BaseModel):
    partido: str
    parlamentares: int
    sim: int
    nao: int
    abstencao: int
    obstrucao: int
    outros: int
    votos_efetivos: int
    orientacao: str | None
    orientacao_por: str | None  # bloco/federação de onde veio a orientação
    seguiram: int | None


class ParlamentarNaVotacao(BaseModel):
    parlamentar_id: int
    nome: str
    partido: str
    uf: str
    voto: str
    registro: str
    efetivo: bool


class DiscursoNaVotacao(BaseModel):
    """Discurso em Plenário: o resumo é o que a própria Casa publica; o texto inteiro fica no
    link. Nunca inferimos posição pelo texto."""

    parlamentar_id: int
    nome: str
    partido: str | None
    uf: str | None
    data: date
    data_hora: datetime | None
    fase: str | None
    tipo: str | None
    sumario: str | None
    url_texto: str | None
    url_video: str | None


class GrupoDiscursos(BaseModel):
    chave: str  # sim | nao | outro | sem_voto
    rotulo: str  # "votou Sim", "votou Não", "outro registro", "falou e não registrou voto"
    quantidade: int
    discursos: list[DiscursoNaVotacao]


class PorUf(BaseModel):
    uf: str
    sim: int
    nao: int
    outros: int
    total: int


class DiscursosDaVotacao(BaseModel):
    """Discursos do dia sobre o projeto, agrupados pelo voto que cada orador registrou nesta
    votação (só quando ela é a última votação nominal do projeto no dia)."""

    total: int
    grupos: list[GrupoDiscursos]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class VotacaoDetalhe(BaseModel):
    casa: str
    id_externo: str
    data: date
    descricao: str
    proposicao: str | None
    proposicao_ementa: str | None
    proposicao_url: str | None
    temas: list[str]
    secreta: bool
    resultado: str | None
    placar: PlacarVotacao
    outros_registros: list[RegistroContado]
    placar_oficial: PlacarOficial | None
    registros: int
    cadeiras: int
    liderancas: list[OrientacaoLideranca]
    outras_bancadas: list[OrientacaoGrupo]
    seguiram_governo: Seguiram
    seguiram_partido: Seguiram
    partidos: list[PartidoNaVotacao]
    parlamentares: list[ParlamentarNaVotacao]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
    # Campos opcionais acrescentados em 2026-10-21; o formato antigo não muda.
    por_uf: list[PorUf] | None = None
    discursos: DiscursosDaVotacao | None = None
