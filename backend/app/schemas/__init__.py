from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ParlamentarResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    casa: str
    nome_parlamentar: str
    partido: str | None
    uf: str
    foto_url: str | None


class Remuneracao(BaseModel):
    subsidio_mensal: float
    vigente_desde: date
    fonte_nome: str
    fonte_url: str


class ParlamentarDetalhe(ParlamentarResumo):
    nome_civil: str | None
    email: str | None
    telefone: str | None
    pagina_url: str | None
    em_exercicio: bool
    em_exercicio_desde: date | None
    fonte_url: str
    atualizado_em: datetime
    remuneracao: Remuneracao


class Localizacao(BaseModel):
    cep: str | None
    uf: str
    estado: str
    municipio: str | None
    codigo_ibge: str | None = None


class RepresentantesResposta(BaseModel):
    localizacao: Localizacao
    deputados: list[ParlamentarResumo]
    senadores: list[ParlamentarResumo]
    atualizado_em: datetime | None


class GastoCategoria(BaseModel):
    categoria: str
    total: float


class GastoMes(BaseModel):
    mes: int
    total: float


class DespesaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes: int
    categoria: str
    fornecedor: str | None
    valor: float
    data: date | None
    url_documento: str | None


class GastosResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    ultimo_mes: int | None
    total: float
    media_casa: float
    por_categoria: list[GastoCategoria]
    por_mes: list[GastoMes]
    maiores_despesas: list[DespesaItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class ProjetoTipo(BaseModel):
    sigla: str
    nome: str
    primeiro_autor: int
    coautor: int


class CandidaturaItem(BaseModel):
    ano: int
    cargo: str
    unidade: str
    partido: str | None
    numero: str | None
    situacao: str | None


class BemItem(BaseModel):
    tipo: str
    descricao: str
    valor: float


class BensAnterior(BaseModel):
    candidatura: CandidaturaItem
    total: float


class BensDeclarados(BaseModel):
    candidatura: CandidaturaItem
    total: float
    quantidade: int
    itens: list[BemItem]
    anterior: BensAnterior | None
    fonte_url: str


class ValorNomeado(BaseModel):
    nome: str
    valor: float


class Campanha(BaseModel):
    candidatura: CandidaturaItem
    receitas_total: float
    receitas_por_origem: list[ValorNomeado]
    despesas_total: float
    despesas_por_tipo: list[ValorNomeado]
    numero_doadores: int
    fonte_url: str


class EleitoDepois(BaseModel):
    id: int
    cargo: str
    unidade: str
    ano: int


class Pessoais(BaseModel):
    ano: int
    idade: int | None
    genero: str | None
    cor_raca: str | None
    grau_instrucao: str | None
    ocupacao: str | None
    estado_civil: str | None
    redes: list[str]


class VotosRecebidos(BaseModel):
    ano: int
    total: int


class CandidaturaResposta(BaseModel):
    candidaturas: list[CandidaturaItem]
    bens: BensDeclarados | None
    campanha: Campanha | None
    pessoais: Pessoais | None = None
    votos: VotosRecebidos | None = None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class EleitoItem(BaseModel):
    id: int
    foto: bool = False
    nome_urna: str
    partido: str | None
    numero: str | None
    situacao: str | None
    uf: str
    parlamentar_id: int | None
    votos: int | None = None
    depois: EleitoDepois | None = None


class ListaEleitos(BaseModel):
    ano_eleicao: int | None
    itens: list[EleitoItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class Chapa(BaseModel):
    cargo: str
    unidade: str
    ano_eleicao: int
    titular: EleitoItem
    vice: EleitoItem | None


class Executivo(BaseModel):
    presidente: Chapa | None
    governador: Chapa | None
    prefeito: Chapa | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class MandatoLocalRef(BaseModel):
    id: int
    casa: str  # "camara" ou "assembleia"


class EleitoDetalhe(EleitoItem):
    mandato_local: MandatoLocalRef | None
    pessoais: Pessoais | None
    cargo: str
    unidade: str
    municipio_ibge: str | None
    ano_eleicao: int
    bens: BensDeclarados | None
    campanha: Campanha | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class ProjetoItem(BaseModel):
    sigla_tipo: str
    numero: int
    ano: int
    ementa: str
    data_apresentacao: date
    situacao: str | None
    virou_lei: bool
    url: str
    primeiro_autor: bool


class ProjetosResposta(BaseModel):
    desde: date
    primeiro_autor: int
    coautor: int
    viraram_norma: int
    media_casa_primeiro_autor: float
    por_tipo: list[ProjetoTipo]
    recentes: list[ProjetoItem]
    viraram_norma_lista: list[ProjetoItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class Justificativa(BaseModel):
    motivo: str
    quantidade: int


class PresencaResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    periodo_inicio: date
    total_votacoes: int
    votou: int
    presente_sem_voto: int
    justificada: int
    nao_compareceu: int
    justificativas: list[Justificativa]
    percentual: float | None
    media_casa_percentual: float | None
    ausencia_detalhada: bool
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class MunicipioInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ibge: str
    nome: str
    uf: str


class EmendaAno(BaseModel):
    ano: int
    total: float


class EmendaParlamentar(BaseModel):
    parlamentar: ParlamentarResumo
    total: float
    do_estado: bool


class EmendaOutroAutor(BaseModel):
    autor_nome: str
    total: float


class EmendaArea(BaseModel):
    area: str
    total: float
    percentual: float


class EmendaAutorDoFavorecido(BaseModel):
    autor_nome: str
    parlamentar_id: int | None


class EmendaFavorecido(BaseModel):
    nome: str
    cnpj: str
    grupo: str
    total: float
    autores: list[EmendaAutorDoFavorecido]


class VereadorItem(BaseModel):
    sessoes: int | None
    presencas: int | None
    votacoes: int
    id: int
    nome: str
    partido: str | None
    foto_url: str | None
    foto_tse: bool
    titular: bool
    em_exercicio: bool
    candidatura_id: int | None
    proposicoes: int
    projetos: int


class CamaraResposta(BaseModel):
    sapl_url: str
    itens: list[VereadorItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class ContagemTipo(BaseModel):
    tipo: str
    total: int


class ProjetoLocalItem(BaseModel):
    tipo: str
    numero: int | None
    ano: int
    ementa: str
    data_apresentacao: date | None
    em_tramitacao: bool | None
    primeiro_autor: bool
    url: str


class PresencaLocal(BaseModel):
    sessoes: int
    presencas: int
    media_casa: float | None


class VotoLocalItem(BaseModel):
    data: date | None
    materia: str
    resultado: str | None
    sim: int
    nao: int
    abstencoes: int
    voto: str
    url: str | None


class VotacoesLocais(BaseModel):
    casa_registra: bool
    total: int  # votações em que aparece (inclusive "Não votou")
    votou: int  # em quantas registrou voto
    pagina: int
    por_pagina: int
    itens: list[VotoLocalItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class CategoriaGasto(BaseModel):
    categoria: str
    valor: float


class GastosLocais(BaseModel):
    ano: int
    ate_mes: int | None
    total: float
    media_casa: float | None
    por_categoria: list[CategoriaGasto]


class VereadorDetalhe(VereadorItem):
    presenca: PresencaLocal | None
    gastos: GastosLocais | None
    casa: str  # "camara" (vereador) ou "assembleia" (deputado estadual)
    uf: str
    municipio_ibge: str | None
    nome_completo: str | None
    email: str | None
    telefone: str | None
    inicio: date | None
    fim: date | None
    proposicoes_por_tipo: list[ContagemTipo]
    lista_projetos: list[ProjetoLocalItem]
    sapl_url: str
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class FornecedorItem(BaseModel):
    fornecedor: str
    documento: str | None
    valor_pago: float
    pagamentos: int


class FornecedoresOrgao(BaseModel):
    orgao: str
    total_pago: float
    itens: list[FornecedorItem]


class FornecedoresResposta(BaseModel):
    ano: int
    orgaos: list[FornecedoresOrgao]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class AreaDespesa(BaseModel):
    nome: str
    valor: float
    percentual: float


class ContasAnterior(BaseModel):
    ano: int
    despesa_paga: float | None
    receita_total: float | None


class ContasMunicipioResposta(BaseModel):
    ano: int
    populacao: int | None
    receita_total: float | None
    despesa_paga: float | None
    despesa_por_habitante: float | None
    camara: float | None
    por_area: list[AreaDespesa]
    anterior: ContasAnterior | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class CanalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo: str
    url: str
    sistema: str | None
    verificado_em: date | None


class CanaisResposta(BaseModel):
    itens: list[CanalItem]


class EmendasMunicipioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    municipio: MunicipioInfo
    desde: int
    total: float
    total_prefeitura: float
    total_entidades: float
    por_ano: list[EmendaAno]
    parlamentares: list[EmendaParlamentar]
    outros_autores: list[EmendaOutroAutor]
    numero_autores: int
    por_area: list[EmendaArea]
    favorecidos: list[EmendaFavorecido]
    numero_favorecidos: int
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class FonteItem(BaseModel):
    dado: str
    orgao: str
    url: str
    atualizado_em: datetime | None


class Criterio(BaseModel):
    id: str
    nome: str
    definicao: str


class ParlamentarNaLista(BaseModel):
    id: int
    casa: str
    nome_parlamentar: str
    partido: str | None
    uf: str
    foto_url: str | None
    gastos: float
    presenca_votou: int
    presenca_total: int
    presenca: float | None
    governo_iguais: int
    governo_total: int
    governo: float | None
    partido_iguais: int
    partido_total: int
    partido_pct: float | None
    projetos: int
    homenagens: int
    normas: int
    emendas: float


class ListaParlamentaresResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    ordenar: str
    ordem: str
    criterios: list[Criterio]
    medias: dict[str, dict[str, float | None]]
    partidos: list[str]
    total: int
    pagina: int
    por_pagina: int
    itens: list[ParlamentarNaLista]
    atualizado_em: datetime | None


class TemaContagem(BaseModel):
    tema: str
    primeiro_autor: int
    coautor: int


class TemasResposta(BaseModel):
    disponivel: bool
    temas: list[TemaContagem]
    homenagens: int


class PlacarResposta(BaseModel):
    iguais: int
    total: int
    percentual: float | None


class VotoItem(BaseModel):
    data: date
    descricao: str
    proposicao: str | None
    proposicao_ementa: str | None
    temas: list[str]
    voto: str
    orientacao_governo: str | None
    maioria_partido: str | None
    partido: str | None
    url: str | None


class VotoComissaoItem(BaseModel):
    data: date
    orgao_sigla: str
    orgao_nome: str | None
    descricao: str
    proposicao: str | None
    proposicao_ementa: str | None
    voto: str
    url: str | None


class ComissaoResumo(BaseModel):
    sigla: str
    nome: str | None
    votacoes: int


class VotosComissoesResposta(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    comissoes: list[ComissaoResumo]
    itens: list[VotoComissaoItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class VotosResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    governo: PlacarResposta | None
    partido: PlacarResposta
    media_governo: float | None
    media_partido: float | None
    temas_disponiveis: list[str]
    tema: str | None
    total: int
    pagina: int
    por_pagina: int
    itens: list[VotoItem]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class TemaLadoALado(BaseModel):
    tema: str
    a: int
    b: int


class Divergencia(BaseModel):
    data: date
    proposicao: str | None
    proposicao_ementa: str | None
    descricao: str
    voto_a: str
    voto_b: str
    url: str | None


class TemaConvergencia(BaseModel):
    tema: str
    iguais: int
    total: int
    percentual: float | None


class Convergencia(BaseModel):
    votacoes_em_comum: int
    iguais: int
    percentual: float | None
    por_tema: list[TemaConvergencia]
    divergencias: list[Divergencia]


class Coautoria(BaseModel):
    sigla_tipo: str
    numero: int
    ano: int
    ementa: str
    data_apresentacao: date
    situacao: str | None
    virou_lei: bool
    url: str


class Coautorias(BaseModel):
    total: int
    itens: list[Coautoria]


class ComparacaoResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    a: ParlamentarResumo
    b: ParlamentarResumo
    numeros_a: ParlamentarNaLista | None
    numeros_b: ParlamentarNaLista | None
    criterios: list[Criterio]
    medias: dict[str, dict[str, float | None]]
    mesma_casa: bool
    temas: list[TemaLadoALado]
    convergencia: Convergencia | None
    coautorias: Coautorias
    atualizado_em: datetime | None


class BuscaItem(BaseModel):
    nome: str
    nome_completo: str | None
    cargo: str
    partido: str | None
    lugar: str
    caminho: str  # endereço do perfil no site


class BuscaPartido(BaseModel):
    sigla: str
    nome: str
    caminho: str  # /partidos/{sigla}


class BuscaResposta(BaseModel):
    itens: list[BuscaItem]  # quem está no cargo hoje
    partidos: list[BuscaPartido]
    pessoas: list[BuscaItem]  # eleições passadas e suplentes, com perfil no site


class LadoLocal(VereadorItem):
    presenca: PresencaLocal | None
    proposicoes_por_tipo: dict[str, int]
    pessoais: Pessoais | None
    votos_recebidos: int | None


class TipoComparado(BaseModel):
    tipo: str
    a: int
    b: int


class DivergenciaLocal(BaseModel):
    data: date | None
    materia: str
    resultado: str | None
    url: str | None
    voto_a: str
    voto_b: str


class ComparacaoLocal(BaseModel):
    casa: str
    a: LadoLocal
    b: LadoLocal
    proposicoes_por_tipo: list[TipoComparado]
    votacoes_em_comum: int
    iguais: int
    divergencias: list[DivergenciaLocal]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class PerfilDaPessoa(BaseModel):
    tipo: str  # parlamentar | vereador | deputado_estadual | candidatura
    id: int
    descricao: str


class PessoaDoPerfil(BaseModel):
    pessoa_id: int


class PessoaResposta(BaseModel):
    id: int
    nome: str
    perfis: list[PerfilDaPessoa]


class ProcessoSituacao(BaseModel):
    """Situação do processo no DataJud (CNJ), na data da consulta."""

    tribunal: str | None
    sigiloso: bool
    classe: str | None
    orgao_julgador: str | None
    data_ajuizamento: date | None
    ultimo_andamento: str | None
    data_ultimo_andamento: date | None
    consultado_em: date


class EventoItem(BaseModel):
    data: date | None
    tipo: str
    descricao: str
    orgao: str | None
    numero_processo: str | None
    situacao: str | None
    fonte_url: str | None
    # Dia da carga que leu o dado na fonte (para dizer "conferido em").
    conferido_em: date | None = None
    processo: ProcessoSituacao | None = None


class LinhaDoTempo(BaseModel):
    pessoa_id: int
    itens: list[EventoItem]


class DocumentoDoCaso(BaseModel):
    tipo: str
    orgao: str
    numero: str | None
    data: date | None
    url: str
    resumo: str


class PessoaNoCaso(BaseModel):
    pessoa_id: int
    nome: str
    papel: str
    data: date | None
    descricao: str
    fonte_url: str | None


class CasoResposta(BaseModel):
    slug: str
    nome: str
    periodo: str | None
    resumo: str
    conferido_em: date
    documentos: list[DocumentoDoCaso]
    pessoas: list[PessoaNoCaso]


class CasoResumo(BaseModel):
    slug: str
    nome: str
    periodo: str | None
    pessoas: int


class PartidoNaLista(BaseModel):
    sigla: str
    cota_fundo_partidario: float
    cota_fefc: float
    receita_total: float
    gasto: float
    repasse_candidatos: float


class PartidosResposta(BaseModel):
    ano: int
    anos_disponiveis: list[int]
    partidos: list[PartidoNaLista]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class CotaMes(BaseModel):
    mes: date
    fundo_partidario: float
    fefc: float


class PartidoValorNomeado(BaseModel):
    nome: str
    valor: float


class PartidoTransferencias(BaseModel):
    recebidas_de_outros_diretorios: float
    enviadas_a_outros_diretorios: float
    repassadas_a_candidatos: float
    outras_enviadas: float


class PartidoGrupoFefc(BaseModel):
    nome: str
    candidatos: int
    valor: float


class PartidoFefcFpResposta(BaseModel):
    ano: int
    fefc_total_partido: float | None
    fefc_por_genero: list[PartidoGrupoFefc]
    fefc_por_cor_raca: list[PartidoGrupoFefc]
    fp_por_genero: list[PartidoGrupoFefc]
    fp_por_cor_raca: list[PartidoGrupoFefc]
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None


class PartidoDetalheResposta(BaseModel):
    sigla: str
    ano: int
    anos_disponiveis: list[int]
    cota_fundo_partidario: float
    cota_fefc: float
    cotas_mensais: list[CotaMes]
    receita_total: float
    gasto: float
    receitas_por_fonte: list[PartidoValorNomeado]
    despesas_por_categoria: list[PartidoValorNomeado]
    transferencias: PartidoTransferencias
    fefc_fp: PartidoFefcFpResposta | None
    fonte_nome: str
    fonte_url: str
    atualizado_em: datetime | None
