// No navegador, a API pública; no servidor (renderização), o endereço interno quando houver
// (em produção, a rede do docker compose), para não sair e voltar pela internet.
const API_URL =
  (typeof window === "undefined" ? process.env.API_URL_INTERNA : undefined) ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

// No servidor, o site se identifica para o firewall da API não aplicar a ele o limite por
// IP (as renderizações de muitos visitantes saem dos mesmos IPs da Vercel). Não é segredo:
// o limite existe contra robôs desatentos, não contra quem queira contorná-lo.
const CABECALHOS: HeadersInit | undefined =
  typeof window === "undefined" ? { "User-Agent": "panoptico-site" } : undefined;

// Endereço público da API (o navegador baixa as fotos direto dela, com cache na CDN).
const API_PUBLICA = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function urlFotoTse(candidaturaId: number) {
  return `${API_PUBLICA}/fotos/${candidaturaId}.webp`;
}

/** Foto de quem tem a foto de outra eleição: usa a candidatura dona da foto, se houver. */
export function urlFotoDe(candidato: { id: number; foto_de?: number | null }) {
  return urlFotoTse(candidato.foto_de ?? candidato.id);
}

/** "foto de 2022", só quando a foto vem de outra eleição da mesma pessoa. */
export function legendaFoto(candidato: { foto_ano?: number | null }): string | null {
  return candidato.foto_ano ? `foto de ${candidato.foto_ano}` : null;
}

export type Casa = "camara" | "senado";

export type ParlamentarResumo = {
  id: number;
  casa: Casa;
  nome_parlamentar: string;
  partido: string | null;
  uf: string;
  foto_url: string | null;
};

export type ParlamentarDetalhe = ParlamentarResumo & {
  /** Id do parlamentar na Casa; com `casa` forma a chave do alvo dos avisos. Ainda opcional: o backend vai expô-lo. */
  id_externo?: string | null;
  nome_civil: string | null;
  email: string | null;
  telefone: string | null;
  pagina_url: string | null;
  em_exercicio: boolean;
  fonte_url: string;
  atualizado_em: string;
  remuneracao: {
    subsidio_mensal: number;
    vigente_desde: string;
    fonte_nome: string;
    fonte_url: string;
  };
};

export type Representantes = {
  localizacao: {
    cep: string | null;
    uf: string;
    estado: string;
    municipio: string | null;
    codigo_ibge: string | null;
  };
  deputados: ParlamentarResumo[];
  senadores: ParlamentarResumo[];
  atualizado_em: string | null;
};

export type Resultado<T> = { ok: true; dados: T } | { ok: false; status: number; mensagem: string };

async function getJson<T>(caminho: string): Promise<Resultado<T>> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`, { headers: CABECALHOS });
  } catch {
    return { ok: false, status: 503, mensagem: "Não foi possível falar com o servidor agora." };
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    const detalhe = typeof corpo?.detail === "string" ? corpo.detail : "Algo deu errado.";
    return { ok: false, status: resposta.status, mensagem: detalhe };
  }
  return { ok: true, dados: (await resposta.json()) as T };
}

export function getRepresentantes(busca: { cep?: string; uf?: string; municipio?: string }) {
  const params = new URLSearchParams();
  if (busca.municipio) params.set("municipio", busca.municipio);
  else if (busca.cep) params.set("cep", busca.cep);
  else if (busca.uf) params.set("uf", busca.uf);
  return getJson<Representantes>(`/representantes?${params}`);
}

export function getParlamentar(id: string) {
  return getJson<ParlamentarDetalhe>(`/parlamentares/${encodeURIComponent(id)}`);
}

export function getSaude() {
  return getJson<{ status: string; banco: string }>("/saude");
}

export type Gastos = {
  ano: number;
  anos_disponiveis: number[];
  ultimo_mes: number | null;
  total: number;
  media_casa: number;
  por_categoria: { categoria: string; total: number }[];
  por_mes: { mes: number; total: number }[];
  maiores_despesas: {
    mes: number;
    categoria: string;
    fornecedor: string | null;
    valor: number;
    data: string | null;
    url_documento: string | null;
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getGastos(id: string, ano?: string) {
  const query = ano ? `?ano=${encodeURIComponent(ano)}` : "";
  return getJson<Gastos>(`/parlamentares/${encodeURIComponent(id)}/gastos${query}`);
}

export type ProjetoItem = {
  sigla_tipo: string;
  numero: number;
  ano: number;
  ementa: string;
  data_apresentacao: string;
  situacao: string | null;
  virou_lei: boolean;
  url: string;
  primeiro_autor: boolean;
};

export type Projetos = {
  desde: string;
  primeiro_autor: number;
  coautor: number;
  viraram_norma: number;
  media_casa_primeiro_autor: number;
  por_tipo: { sigla: string; nome: string; primeiro_autor: number; coautor: number }[];
  recentes: ProjetoItem[];
  viraram_norma_lista: ProjetoItem[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

type CandidaturaItem = {
  ano: number;
  cargo: string;
  unidade: string;
  partido: string | null;
  numero: string | null;
  situacao: string | null;
};

export type CandidaturaTse = {
  candidaturas: CandidaturaItem[];
  bens: {
    candidatura: CandidaturaItem;
    total: number;
    quantidade: number;
    itens: { tipo: string; descricao: string; valor: number }[];
    anterior: { candidatura: CandidaturaItem; total: number } | null;
    fonte_url: string;
  } | null;
  campanha: {
    candidatura: CandidaturaItem;
    receitas_total: number;
    receitas_por_origem: { nome: string; valor: number }[];
    despesas_total: number;
    despesas_por_tipo: { nome: string; valor: number }[];
    numero_doadores: number;
    fonte_url: string;
  } | null;
  pessoais?: Pessoais | null;
  votos?: { ano: number; total: number } | null;
  eleito_2026?: EleitoFuturo | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

/** Eleito (ou candidato no 2º turno) de uma eleição cuja posse ainda não aconteceu. */
export type EleitoFuturo = {
  id: number;
  nome_urna: string;
  partido: string | null;
  numero: string | null;
  uf: string;
  cargo: string;
  unidade: string;
  ano_eleicao: number;
  situacao: string | null;
  situacao_tse: string | null;
  segundo_turno: boolean;
  data_segundo_turno: string | null;
  posse: string;
  votos: number | null;
  parlamentar_id: number | null;
  /** Já exerce hoje um mandato federal (por exemplo, reeleito). */
  ja_no_cargo: boolean;
  vice: string | null;
  /** Onde o site abre a pessoa: o perfil de quem já está no cargo, se houver. */
  perfil: string;
  foto?: boolean;
  foto_de?: number | null;
  foto_ano?: number | null;
};

export type EleitosFuturos = {
  ano_eleicao: number | null;
  presidente: EleitoFuturo[];
  governador: EleitoFuturo[];
  senadores: EleitoFuturo[];
  deputados_federais: EleitoFuturo[];
  deputados_estaduais: EleitoFuturo[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getEleitos2026(uf: string) {
  return getJson<EleitosFuturos>(`/estados/${encodeURIComponent(uf)}/eleitos-2026`);
}

export type Eleito = {
  id: number;
  foto?: boolean;
  /** Candidatura dona da foto, quando a foto é de outra eleição da mesma pessoa. */
  foto_de?: number | null;
  foto_ano?: number | null;
  nome_urna: string;
  partido: string | null;
  numero: string | null;
  situacao: string | null;
  uf: string;
  parlamentar_id: number | null;
  votos?: number | null;
  depois?: { id: number; cargo: string; unidade: string; ano: number } | null;
};

export type Pessoais = {
  ano: number;
  idade: number | null;
  genero: string | null;
  cor_raca: string | null;
  grau_instrucao: string | null;
  ocupacao: string | null;
  estado_civil: string | null;
  redes: string[];
};

export type ListaEleitos = {
  ano_eleicao: number | null;
  itens: Eleito[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

/** Bens, campanha e dados da candidatura de uma eleição cuja posse ainda não aconteceu. */
export type EleicaoRecente = Pick<CandidaturaTse, "bens" | "campanha" | "fonte_nome" | "fonte_url" | "atualizado_em"> & {
  id: number;
  ano_eleicao: number;
  cargo: string;
  unidade: string;
  pessoais: Pessoais | null;
};

export type EleitoDetalhe = Eleito &
  Pick<CandidaturaTse, "bens" | "campanha" | "fonte_nome" | "fonte_url" | "atualizado_em"> & {
    /** Quando a própria casa (SAPL) lista a pessoa no cargo: o perfil com a atividade. */
    mandato_local: { id: number; casa: "camara" | "assembleia" } | null;
    pessoais: Pessoais | null;
    cargo: string;
    unidade: string;
    municipio_ibge: string | null;
    ano_eleicao: number;
    eleito_2026?: EleitoFuturo | null;
    /** Caminho do perfil principal da pessoa; a página da candidatura nova redireciona para ele. */
    perfil_principal?: string | null;
    eleicao_recente?: EleicaoRecente | null;
  };

export type Chapa = {
  cargo: string;
  unidade: string;
  ano_eleicao: number;
  titular: Eleito;
  vice: Eleito | null;
};

export type Executivo = {
  presidente: Chapa | null;
  governador: Chapa | null;
  prefeito: Chapa | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getExecutivo(uf: string, municipio?: string | null) {
  const params = new URLSearchParams({ uf });
  if (municipio) params.set("municipio", municipio);
  return getJson<Executivo>(`/executivo?${params}`);
}

export type VereadorItem = {
  id: number;
  nome: string;
  partido: string | null;
  foto_url: string | null;
  foto_tse: boolean;
  titular: boolean;
  em_exercicio: boolean;
  candidatura_id: number | null;
  proposicoes: number;
  projetos: number;
  /** Sessões com presença registrada no período e em quantas estava (nulo se a casa não registra). */
  sessoes: number | null;
  presencas: number | null;
  /** Votações nominais em que votou (ano atual e anterior). */
  votacoes: number;
};

export type Camara = {
  sapl_url: string;
  itens: VereadorItem[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type VereadorDetalhe = VereadorItem & {
  eleito_2026?: EleitoFuturo | null;
  eleicao_recente?: EleicaoRecente | null;
  /** "camara" (vereador) ou "assembleia" (deputado estadual). */
  casa: "camara" | "assembleia";
  uf: string;
  presenca: { sessoes: number; presencas: number; media_casa: number | null } | null;
  /** Gastos do gabinete (verba indenizatória), onde a casa publica. */
  gastos: {
    ano: number;
    ate_mes: number | null;
    total: number;
    media_casa: number | null;
    /** Fonte parcial: a média saiu só de quem consta nela; `media_descricao` diz "X dos Y". */
    media_parcial?: boolean;
    media_descricao?: string | null;
    por_categoria: { categoria: string; valor: number }[];
    /** Data da última carga que atualizou os gastos (pode ser anterior à do resto do perfil). */
    atualizado_em?: string | null;
    /** O que a planilha traz mas não entra na soma por mês (ex.: comprovantes sem data). */
    fora_da_soma?: { linhas: number; valor: number; linhas_valor_ilegivel: number; motivo: string } | null;
  } | null;
  municipio_ibge: string | null;
  nome_completo: string | null;
  email: string | null;
  telefone: string | null;
  inicio: string | null;
  fim: string | null;
  proposicoes_por_tipo: { tipo: string; total: number }[];
  lista_projetos: {
    tipo: string;
    numero: number | null;
    ano: number;
    ementa: string;
    data_apresentacao: string | null;
    em_tramitacao: boolean | null;
    primeiro_autor: boolean;
    url: string;
  }[];
  sapl_url: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getCamara(ibge: string) {
  return getJson<Camara>(`/municipios/${encodeURIComponent(ibge)}/camara`);
}

export type VotacoesLocais = {
  casa_registra: boolean;
  /** Votações em que aparece, inclusive como "Não votou". */
  total: number;
  /** Em quantas registrou voto. */
  votou: number;
  pagina: number;
  por_pagina: number;
  itens: {
    data: string | null;
    materia: string;
    resultado: string | null;
    sim: number;
    nao: number;
    abstencoes: number;
    voto: string;
    url: string | null;
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getVotacoesLocais(id: string, pagina?: string) {
  const params = pagina ? `?pagina=${encodeURIComponent(pagina)}` : "";
  return getJson<VotacoesLocais>(`/vereadores/${encodeURIComponent(id)}/votacoes${params}`);
}

export function getAssembleia(uf: string) {
  return getJson<Camara>(`/estados/${encodeURIComponent(uf)}/assembleia`);
}

export function getVereador(id: string) {
  return getJson<VereadorDetalhe>(`/vereadores/${encodeURIComponent(id)}`);
}

export type Fornecedores = {
  ano: number;
  orgaos: {
    orgao: string;
    total_pago: number;
    itens: { fornecedor: string; nome_omitido?: boolean; documento: string | null; valor_pago: number; pagamentos: number }[];
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getFornecedores(ibge: string) {
  return getJson<Fornecedores>(`/municipios/${encodeURIComponent(ibge)}/fornecedores`);
}

export type ContasMunicipio = {
  ano: number;
  populacao: number | null;
  receita_total: number | null;
  despesa_paga: number | null;
  despesa_por_habitante: number | null;
  media_uf_despesa_por_habitante?: number | null;
  municipios_na_media?: number | null;
  media_uf_descricao?: string | null;
  camara: number | null;
  por_area: { nome: string; valor: number; percentual: number }[];
  anterior: { ano: number; despesa_paga: number | null; receita_total: number | null } | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getContas(ibge: string) {
  return getJson<ContasMunicipio>(`/municipios/${encodeURIComponent(ibge)}/contas`);
}

export type Canal = { tipo: string; url: string; sistema: string | null; verificado_em: string | null };

export function getCanais(ibge: string) {
  return getJson<{ itens: Canal[] }>(`/municipios/${encodeURIComponent(ibge)}/canais`);
}

export function getVereadores(ibge: string) {
  return getJson<ListaEleitos>(`/municipios/${encodeURIComponent(ibge)}/vereadores`);
}

export function getDeputadosEstaduais(uf: string) {
  return getJson<ListaEleitos>(`/estados/${encodeURIComponent(uf)}/deputados-estaduais`);
}

export function getEleito(id: string) {
  return getJson<EleitoDetalhe>(`/eleitos/${encodeURIComponent(id)}`);
}

export type VotosComissoes = {
  total: number;
  pagina: number;
  por_pagina: number;
  comissoes: { sigla: string; nome: string | null; votacoes: number }[];
  itens: {
    data: string;
    orgao_sigla: string;
    orgao_nome: string | null;
    descricao: string;
    proposicao: string | null;
    proposicao_ementa: string | null;
    voto: string;
    url: string | null;
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getVotosComissoes(id: string, pagina?: string) {
  const params = new URLSearchParams();
  if (pagina) params.set("pagina", pagina);
  return getJson<VotosComissoes>(`/parlamentares/${encodeURIComponent(id)}/votos-comissoes?${params}`);
}

export function getCandidatura(id: string) {
  return getJson<CandidaturaTse>(`/parlamentares/${encodeURIComponent(id)}/candidatura`);
}

export function getProjetos(id: string) {
  return getJson<Projetos>(`/parlamentares/${encodeURIComponent(id)}/projetos`);
}

export type DestinoEmendaItem = {
  emenda_codigo: string;
  ano_emenda: number;
  tipo: "convenio" | "especial";
  identificador: string;
  situacao: string | null;
  relatorio_gestao: string | null;
  beneficiario: string | null;
  nome_omitido?: boolean;
  beneficiario_cnpj: string | null;
  uf: string | null;
  orgao_concedente: string | null;
  objeto: string | null;
  valor_total: number | null;
  valor_repassado: number | null;
  valor_contrapartida: number | null;
  inicio_vigencia: string | null;
  fim_vigencia: string | null;
  fonte_url: string;
};

export type DestinoEmendas = {
  desde: number;
  quantidade: number;
  valor_total: number;
  valor_repassado: number;
  por_situacao: { tipo: string; situacao: string | null; quantidade: number; valor_total: number }[];
  relatorios_de_gestao: { situacao: string | null; quantidade: number }[];
  itens: DestinoEmendaItem[];
  limite: number;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getDestinoEmendas(id: string) {
  return getJson<DestinoEmendas>(`/parlamentares/${encodeURIComponent(id)}/emendas-destino`);
}

export type EmendasRelator = {
  ano: number;
  quantidade: number;
  valor_solicitado: number;
  beneficiarios: number;
  por_orgao: { orgao: string; quantidade: number; valor: number }[];
  itens: {
    numero: number;
    data_cadastro: string | null;
    beneficiario: string;
    uf: string | null;
    orgao: string | null;
    objeto: string | null;
    valor_solicitado: number;
  }[];
  limite: number;
  fonte_nome: string;
  fonte_url: string;
  arquivo_url: string;
  atualizado_em: string | null;
};

export function getEmendasRelator(id: string) {
  return getJson<EmendasRelator>(`/parlamentares/${encodeURIComponent(id)}/emendas-relator`);
}

export type Presenca = {
  ano: number;
  anos_disponiveis: number[];
  periodo_inicio: string;
  total_votacoes: number;
  votou: number;
  presente_sem_voto: number;
  justificada: number;
  nao_compareceu: number;
  justificativas: { motivo: string; quantidade: number }[];
  percentual: number | null;
  media_casa_percentual: number | null;
  ausencia_detalhada: boolean;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getPresenca(id: string, ano?: string) {
  const query = ano ? `?ano=${encodeURIComponent(ano)}` : "";
  return getJson<Presenca>(`/parlamentares/${encodeURIComponent(id)}/presenca${query}`);
}

export type EmendasMunicipio = {
  municipio: { ibge: string; nome: string; uf: string };
  desde: number;
  total: number;
  total_prefeitura: number;
  total_entidades: number;
  por_ano: { ano: number; total: number }[];
  parlamentares: { parlamentar: ParlamentarResumo; total: number; do_estado: boolean }[];
  outros_autores: {
    autor_nome: string;
    total: number;
    parlamentar_id?: number | null;
    pessoa_id?: number | null;
    com_mandato_atual?: boolean;
  }[];
  numero_autores: number;
  por_area: { area: string; total: number; percentual: number }[];
  favorecidos: {
    nome: string;
    cnpj: string;
    grupo: "prefeitura" | "entidade";
    total: number;
    autores: { autor_nome: string; parlamentar_id: number | null }[];
  }[];
  numero_favorecidos: number;
  populacao?: number | null;
  por_habitante?: number | null;
  media_uf_por_habitante?: number | null;
  municipios_na_media?: number | null;
  media_uf_descricao?: string | null;
  // Campos novos (18/10/2026); ausentes em APIs antigas, então todos opcionais.
  periodo?: { inicio: number | null; fim: number | null };
  tipos?: EmendaTipo[];
  total_geral?: number;
  por_habitante_geral?: number | null;
  media_uf_por_habitante_geral?: number | null;
  numero_outros_autores?: number;
  autores_com_mandato?: number;
  autores_sem_mandato?: number;
  colegiados?: EmendaColegiado[];
  previsto?: EmendasPrevistas | null;
  convenios?: EmendasConvenios | null;
  sem_codigo_descricao?: string;
  sem_identificacao?: EmendaSemIdentificacao | null;
  /** Emendas de deputados estaduais (outra esfera, nunca somadas às federais); só onde há fonte. */
  estaduais?: EmendasEstaduaisMunicipio | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type EmendaEstadualSomas = { previsto: number; empenhado: number; pago: number; emendas: number };

export type EmendasEstaduaisMunicipio = {
  uf: string;
  casa: string;
  total_previsto: number;
  total_empenhado: number;
  /** Falso quando a fonte da UF não publica o empenhado (SE); a API antiga não manda o campo. */
  empenhado_informado?: boolean;
  total_pago: number;
  emendas: number;
  por_autor: (EmendaEstadualSomas & {
    autor_nome: string;
    tipo: string;
    pessoa_id: number | null;
    mandato_id: number | null;
    em_exercicio: boolean;
  })[];
  por_ano: (EmendaEstadualSomas & { ano: number })[];
  favorecidos: (EmendaEstadualSomas & { nome: string; cnpj: string | null })[];
  numero_favorecidos: number;
  somado_ao_federal: boolean;
  descricao: string;
  recorte: string;
  termos: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type EmendasDeputadoEstadual = {
  mandato_id: number;
  nome: string;
  uf: string;
  casa: string;
  periodo: { inicio: number | null; fim: number | null };
  total_previsto: number;
  total_empenhado: number;
  /** Falso quando a fonte da UF não publica o empenhado (SE); a API antiga não manda o campo. */
  empenhado_informado?: boolean;
  total_pago: number;
  emendas: number;
  media_casa_pago: number | null;
  deputados_na_media: number;
  media_parcial?: boolean;
  media_descricao: string;
  por_ano: (EmendaEstadualSomas & { ano: number })[];
  por_municipio: (EmendaEstadualSomas & { ibge: string | null; nome: string })[];
  numero_municipios: number;
  itens: {
    codigo: string;
    ano: number;
    municipio_ibge: string | null;
    municipio_nome: string;
    favorecido: string;
    orgao: string | null;
    objeto: string | null;
    situacao: string | null;
    previsto: number;
    empenhado: number | null;
    pago: number;
  }[];
  numero_itens: number;
  descricao: string;
  recorte: string;
  termos: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getEmendasDeputadoEstadual(mandatoId: string | number) {
  return getJson<EmendasDeputadoEstadual>(`/deputados-estaduais/${encodeURIComponent(String(mandatoId))}/emendas`);
}

export type EmendaTipo = {
  tipo: string;
  rotulo: string;
  rotulo_oficial: string;
  total: number;
  pagamentos: number;
  /** Parte do total paga sem código de emenda e sem autor na fonte; ausente em APIs antigas. */
  sem_codigo_total?: number;
  sem_codigo_pagamentos?: number;
};

export type EmendaSemIdentificacao = {
  total: number;
  pagamentos: number;
  /** AAAAMM */
  primeiro_pagamento: number | null;
  ultimo_pagamento: number | null;
  incluido_no_total_geral?: boolean;
  descricao?: string;
};

export type EmendaColegiado = { autor_nome: string; tipo: string; rotulo: string; total: number };

export type EmendasPrevistas = {
  planos: number;
  valor_planos: number;
  impedidos?: {
    planos: number;
    valor: number;
    motivos: { situacao: string; planos: number; valor: number }[];
  } | null;
  planos_com_pagamento: number;
  valor_planos_com_pagamento: number;
  planos_sem_pagamento: number;
  valor_sem_pagamento: number;
  sem_pagamento: {
    identificador: string;
    emenda_codigo: string;
    ano: number;
    autor_nome: string | null;
    parlamentar_id: number | null;
    com_mandato_atual: boolean;
    beneficiario: string | null;
    situacao: string | null;
    valor: number;
    fonte_url: string;
  }[];
  descricao: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type EmendasConvenios = {
  quantidade: number;
  valor_total: number;
  valor_liberado: number;
  itens: {
    identificador: string;
    emendas: string[];
    autores: string[];
    beneficiario: string | null;
    situacao: string | null;
    valor_total: number;
    valor_liberado: number;
  }[];
  descricao: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getEmendasMunicipio(ibge: string) {
  return getJson<EmendasMunicipio>(`/municipios/${encodeURIComponent(ibge)}/emendas`);
}

export type Fonte = { dado: string; orgao: string; url: string; atualizado_em: string | null };

export function getFontes() {
  return getJson<Fonte[]>("/fontes");
}

export type Municipio = { ibge: string; nome: string; uf: string };

export function getMunicipios(uf: string) {
  return getJson<Municipio[]>(`/municipios?uf=${encodeURIComponent(uf)}`);
}

export type CriterioId = "nome" | "gastos" | "presenca" | "projetos" | "normas" | "emendas" | "governo";

export type ParlamentarNaLista = ParlamentarResumo & {
  gastos: number;
  presenca_votou: number;
  presenca_total: number;
  presenca: number | null;
  governo_iguais: number;
  governo_total: number;
  governo: number | null;
  partido_iguais: number;
  partido_total: number;
  partido_pct: number | null;
  projetos: number;
  homenagens: number;
  normas: number;
  emendas: number;
};

export type ListaParlamentares = {
  ano: number;
  anos_disponiveis: number[];
  ordenar: CriterioId;
  ordem: "asc" | "desc";
  criterios: { id: CriterioId; nome: string; definicao: string }[];
  medias: Record<Casa, Record<string, number | null>>;
  partidos: string[];
  por_casa: Record<Casa, number>;
  total: number;
  pagina: number;
  por_pagina: number;
  itens: ParlamentarNaLista[];
  atualizado_em: string | null;
};

export type FiltrosLista = {
  busca?: string;
  casa?: string;
  uf?: string;
  partido?: string;
  ordenar?: string;
  ordem?: string;
  ano?: string;
  pagina?: string;
};

export function getParlamentares(filtros: FiltrosLista) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) if (valor) params.set(chave, valor);
  return getJson<ListaParlamentares>(`/parlamentares?${params}`);
}

export type Temas = {
  disponivel: boolean;
  temas: { tema: string; primeiro_autor: number; coautor: number }[];
  homenagens: number;
};

export function getTemas(id: string) {
  return getJson<Temas>(`/parlamentares/${encodeURIComponent(id)}/temas`);
}

export type Placar = { iguais: number; total: number; percentual: number | null };

export type VotoItem = {
  data: string;
  descricao: string;
  proposicao: string | null;
  proposicao_ementa: string | null;
  temas: string[];
  voto: string;
  orientacao_governo: string | null;
  maioria_partido: string | null;
  partido: string | null;
  url: string | null;
  /** Id da votação na fonte, para o link ao explicador (/votacao/[casa]/[id]). */
  id_externo?: string | null;
  /** Id do projeto na Casa, para o link /projeto/[casa]/[id]. */
  proposicao_id_externo?: string | null;
};

export type Votos = {
  ano: number;
  anos_disponiveis: number[];
  governo: Placar | null;
  partido: Placar;
  media_governo: number | null;
  media_partido: number | null;
  temas_disponiveis: string[];
  tema: string | null;
  total: number;
  pagina: number;
  por_pagina: number;
  itens: VotoItem[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getVotos(id: string, opcoes: { ano?: string; tema?: string; pagina?: string }) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(opcoes)) if (valor) params.set(chave, valor);
  return getJson<Votos>(`/parlamentares/${encodeURIComponent(id)}/votos?${params}`);
}

export type Comparacao = {
  ano: number;
  anos_disponiveis: number[];
  a: ParlamentarResumo;
  b: ParlamentarResumo;
  numeros_a: ParlamentarNaLista | null;
  numeros_b: ParlamentarNaLista | null;
  criterios: { id: CriterioId; nome: string; definicao: string }[];
  medias: Record<Casa, Record<string, number | null>>;
  mesma_casa: boolean;
  temas: { tema: string; a: number; b: number }[];
  convergencia: {
    votacoes_em_comum: number;
    iguais: number;
    percentual: number | null;
    por_tema: { tema: string; iguais: number; total: number; percentual: number | null }[];
    divergencias: {
      data: string;
      proposicao: string | null;
      proposicao_ementa: string | null;
      descricao: string;
      voto_a: string;
      voto_b: string;
      url: string | null;
    }[];
  } | null;
  coautorias: {
    total: number;
    itens: Omit<ProjetoItem, "primeiro_autor">[];
  };
  atualizado_em: string | null;
};

export function getComparacao(a: string, b: string, ano?: string) {
  const params = new URLSearchParams({ a, b });
  if (ano) params.set("ano", ano);
  return getJson<Comparacao>(`/comparar?${params}`);
}

/** Convergência de um par (i < j, índices em `pessoas`); `convergencia` é null se forem de Casas diferentes. */
export type ConvergenciaDoPar = {
  i: number;
  j: number;
  mesma_casa: boolean;
  convergencia: NonNullable<Comparacao["convergencia"]> | null;
};

/** Comparação de 2 a 4 parlamentares (chamada com `ids`). Listas alinhadas à ordem de `ids`. */
export type ComparacaoN = {
  ano: number;
  anos_disponiveis: number[];
  pessoas: ParlamentarResumo[];
  numeros: (ParlamentarNaLista | null)[];
  criterios: Comparacao["criterios"];
  medias: Comparacao["medias"];
  mesma_casa: boolean;
  temas: { tema: string; valores: number[] }[];
  convergencia: ConvergenciaDoPar[];
  coautorias: { i: number; j: number; total: number; itens: Comparacao["coautorias"]["itens"] }[];
  atualizado_em: string | null;
};

/** De 2 a 4 ids distintos (422 fora disso). */
export function getComparacaoN(ids: (string | number)[], ano?: string) {
  const params = new URLSearchParams({ ids: ids.join(",") });
  if (ano) params.set("ano", ano);
  return getJson<ComparacaoN>(`/comparar?${params}`);
}

export type ResultadoBusca = {
  nome: string;
  nome_completo: string | null;
  cargo: string;
  partido: string | null;
  lugar: string;
  /** Endereço do perfil no site. */
  caminho: string;
};

export type PartidoBuscado = { sigla: string; nome: string; caminho: string };

export type RespostaBusca = {
  /** Quem está no cargo hoje. */
  itens: ResultadoBusca[];
  partidos: PartidoBuscado[];
  /** Eleições passadas e suplentes, com perfil no site. */
  pessoas: ResultadoBusca[];
  /** Eleitos que ainda não tomaram posse (e quem disputa o 2º turno). */
  eleitos_2026: ResultadoBusca[];
};

/** Busca por nome: pessoas de todos os níveis, partidos e eleitos de eleições passadas. */
export async function getBusca(q: string) {
  // `nome` repetido de propósito: a API anterior só lê `nome` e não manda `partidos`
  // nem `pessoas`. Assim a busca segue funcionando se o site for publicado antes da API.
  const termo = encodeURIComponent(q);
  const resposta = await getJson<RespostaBusca>(`/busca?q=${termo}&nome=${termo}`);
  if (resposta.ok) {
    resposta.dados.partidos ??= [];
    resposta.dados.pessoas ??= [];
    resposta.dados.eleitos_2026 ??= [];
  }
  return resposta;
}

export type LadoLocal = VereadorItem & {
  presenca: { sessoes: number; presencas: number; media_casa: number | null } | null;
  proposicoes_por_tipo: Record<string, number>;
  pessoais: Pessoais | null;
  votos_recebidos: number | null;
};

export type ComparacaoLocal = {
  casa: "camara" | "assembleia";
  a: LadoLocal;
  b: LadoLocal;
  proposicoes_por_tipo: { tipo: string; a: number; b: number }[];
  votacoes_em_comum: number;
  iguais: number;
  divergencias: {
    data: string | null;
    materia: string;
    resultado: string | null;
    url: string | null;
    voto_a: string;
    voto_b: string;
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

/** Dois da mesma câmara ou assembleia, lado a lado. */
export function getComparacaoLocal(a: string, b: string) {
  return getJson<ComparacaoLocal>(`/comparar/local?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
}

/** De 2 a 4 da mesma câmara ou assembleia (chamada com `ids`). */
export type ComparacaoLocalN = {
  casa: "camara" | "assembleia";
  pessoas: LadoLocal[];
  proposicoes_por_tipo: { tipo: string; valores: number[] }[];
  convergencia: {
    i: number;
    j: number;
    votacoes_em_comum: number;
    iguais: number;
    divergencias: ComparacaoLocal["divergencias"]; // voto_a é de i, voto_b é de j
  }[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getComparacaoLocalN(ids: (string | number)[]) {
  return getJson<ComparacaoLocalN>(`/comparar/local?ids=${ids.map((i) => encodeURIComponent(i)).join(",")}`);
}

export type ProcessoSituacao = {
  tribunal: string | null;
  sigiloso: boolean;
  classe: string | null;
  orgao_julgador: string | null;
  data_ajuizamento: string | null;
  ultimo_andamento: string | null;
  data_ultimo_andamento: string | null;
  consultado_em: string;
};

export type EventoItem = {
  data: string | null;
  tipo: string;
  descricao: string;
  orgao: string | null;
  numero_processo: string | null;
  situacao: string | null;
  fonte_url: string | null;
  conferido_em: string | null;
  processo: ProcessoSituacao | null;
};

export type LinhaDoTempo = { pessoa_id: number; itens: EventoItem[] };

/** Os perfis do site, como a API os chama em /pessoas/de. */
export type TipoDePerfil = "parlamentar" | "candidatura" | "vereador" | "deputado_estadual";

/** Linha do tempo da pessoa por trás de um perfil. 404 quando o perfil não está ligado a
 * uma pessoa por vínculo forte ou revisado (aí a seção não aparece). */
export async function getLinhaDoTempo(tipo: TipoDePerfil, id: string): Promise<Resultado<LinhaDoTempo>> {
  const pessoa = await getJson<{ pessoa_id: number }>(`/pessoas/de?tipo=${tipo}&id=${encodeURIComponent(id)}`);
  if (!pessoa.ok) return pessoa;
  return getJson<LinhaDoTempo>(`/pessoas/${pessoa.dados.pessoa_id}/eventos`);
}

export type PartidoNaLista = {
  sigla: string;
  cota_fundo_partidario: number;
  cota_fefc: number;
  receita_total: number;
  gasto: number;
  repasse_candidatos: number;
};

export type Partidos = {
  ano: number;
  anos_disponiveis: number[];
  partidos: PartidoNaLista[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getPartidos(ano?: string) {
  const query = ano ? `?ano=${encodeURIComponent(ano)}` : "";
  return getJson<Partidos>(`/partidos${query}`);
}

export type GrupoFefc = { nome: string; candidatos: number; valor: number };

export type PartidoDetalhe = {
  sigla: string;
  ano: number;
  anos_disponiveis: number[];
  cota_fundo_partidario: number;
  cota_fefc: number;
  cotas_mensais: { mes: string; fundo_partidario: number; fefc: number }[];
  receita_total: number;
  gasto: number;
  receitas_por_fonte: { nome: string; valor: number }[];
  despesas_por_categoria: { nome: string; valor: number }[];
  transferencias: {
    recebidas_de_outros_diretorios: number;
    enviadas_a_outros_diretorios: number;
    repassadas_a_candidatos: number;
    outras_enviadas: number;
  };
  fefc_fp: {
    ano: number;
    fefc_total_partido: number | null;
    fefc_por_genero: GrupoFefc[];
    fefc_por_cor_raca: GrupoFefc[];
    fp_por_genero: GrupoFefc[];
    fp_por_cor_raca: GrupoFefc[];
    fonte_nome: string;
    fonte_url: string;
    atualizado_em: string | null;
  } | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getPartido(sigla: string, ano?: string) {
  const query = ano ? `?ano=${encodeURIComponent(ano)}` : "";
  return getJson<PartidoDetalhe>(`/partidos/${encodeURIComponent(sigla)}${query}`);
}

export type ContratoPncp = {
  fornecedor_cnpj: string;
  fornecedor_nome: string | null;
  nome_omitido?: boolean;
  orgao: string | null;
  municipio: string | null;
  uf: string | null;
  objeto: string | null;
  valor: number | null;
  /** O valor informado ao PNCP parece digitado errado: fora do total, com aviso. */
  valor_suspeito: boolean;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  publicado_em: string;
  url: string;
};

export type ContratosDaPessoa = {
  pessoa_id: number;
  empresas: { cnpj: string; nome: string | null; nome_omitido?: boolean; qualificacao: string | null; contratos: number }[];
  total_contratos: number;
  valor_total: number;
  contratos_suspeitos: number;
  itens: ContratoPncp[];
  cobertura_desde: string | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

/** Contratos públicos (PNCP) de empresas de que a pessoa é sócia. */
export function getContratosDaPessoa(pessoaId: number) {
  return getJson<ContratosDaPessoa>(`/pessoas/${pessoaId}/contratos`);
}

export type FornecedoresPncp = {
  ano: number;
  itens: {
    fornecedor_cnpj: string;
    fornecedor: string | null;
    nome_omitido?: boolean;
    valor: number;
    contratos: number;
    /** O CNPJ também aparece como órgão contratante no PNCP (repasse entre órgãos). */
    ente_publico?: boolean;
  }[];
  /** Valores informados ao PNCP que parecem incorretos: fora do ranking e da soma. */
  suspeitos: { fornecedor_cnpj: string; fornecedor: string | null; nome_omitido?: boolean; valor: number; contratos: number; url: string }[];
  soma_ate: string | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getFornecedoresPncp(ibge: string) {
  return getJson<FornecedoresPncp>(`/municipios/${encodeURIComponent(ibge)}/fornecedores-pncp`);
}

export type SancaoItem = {
  data: string | null;
  tipo: string;
  descricao: string;
  orgao: string | null;
  numero_processo: string | null;
  situacao: string | null;
  fonte: string | null;
  fonte_url: string | null;
  regra: string | null;
  ligacao: string | null;
};

export type Sancoes = {
  pessoa_id: number;
  itens: SancaoItem[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getSancoes(pessoaId: number) {
  return getJson<Sancoes>(`/pessoas/${pessoaId}/sancoes`);
}

export type CargoFederal = {
  funcao: string | null;
  sigla: string | null;
  nivel: string | null;
  orgao: string | null;
  origem: string | null;
  primeiro_mes: string | null;
  ultimo_mes: string | null;
  consta_no_cadastro_mais_recente: boolean;
};

export type ViagensPorAno = {
  ano: number;
  viagens: number;
  diarias: number;
  passagens: number;
  outros: number;
  devolucao: number;
  ultima_viagem: string | null;
  media_casa_viagens: number | null;
  media_casa_valor: number | null;
};

export type CartaoPorAnoEOrgao = {
  ano: number;
  orgao: string | null;
  transacoes: number;
  total: number;
  saques: number;
  media_casa_total: number | null;
};

export type ServicoFederal = {
  pessoa_id: number;
  regra: string | null;
  ligacao: string | null;
  cargos: CargoFederal[];
  viagens_por_ano: ViagensPorAno[];
  cartao_por_ano_e_orgao: CartaoPorAnoEOrgao[];
  media_da_casa: { parlamentares_em_exercicio: number; descricao: string } | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getServicoFederal(pessoaId: number) {
  return getJson<ServicoFederal>(`/pessoas/${pessoaId}/servico-federal`);
}

export type CandidaturaDaCarreira = {
  ano: number;
  cargo: string;
  uf: string | null;
  unidade: string | null;
  municipio: string | null;
  partido: string | null;
  numero: string | number | null;
  situacao: string | null;
  eleito: boolean | null;
  votos: number | null;
  bens_total: number | null;
  bens_declarados: boolean | null;
  fonte_url: string | null;
  regra: string | null;
  ligacao: string | null;
};

export type Carreira = {
  pessoa_id: number;
  itens: CandidaturaDaCarreira[];
  recorte: { texto: string; anos_candidaturas: number[]; anos_bens: number[] };
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getCarreira(pessoaId: number) {
  return getJson<Carreira>(`/pessoas/${pessoaId}/carreira`);
}


export type VotoTema = {
  tema: string;
  total_votacoes: number;
  votou: number;
  percentual: number | null;
  media_casa_percentual: number | null;
  media_casa_votou: number | null;
  governo_iguais: number;
  governo_total: number;
};

export type VotosPorTema = {
  ano: number;
  anos_disponiveis: number[];
  periodo_inicio: string;
  temas: VotoTema[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getVotosPorTema(id: string, ano?: string) {
  const query = ano ? `?ano=${encodeURIComponent(ano)}` : "";
  return getJson<VotosPorTema>(`/parlamentares/${encodeURIComponent(id)}/votos-por-tema${query}`);
}

// ---- Comparador do 2º turno ----------------------------------------------------------

export type CandidatoSegundoTurno = {
  id: number;
  nome_urna: string;
  numero: string | null;
  partido: string | null;
  foto: boolean;
  foto_de?: number | null;
  foto_ano?: number | null;
  foto_url: string | null;
  vice: { id: number; nome_urna: string; partido: string | null; foto: boolean; foto_de?: number | null; foto_ano?: number | null } | null;
  votos_1turno: number | null;
  /** Só depois do resultado: os votos do 2º turno (a fonte troca a coluna). */
  votos_2turno: number | null;
  /** Nulo enquanto o 2º turno não tem resultado. */
  eleito: boolean | null;
  bens: {
    ano: number;
    total: number;
    quantidade: number;
    maiores: { tipo: string; descricao: string; valor: number }[];
    anterior: { ano: number; cargo: string; total: number | null } | null;
    fonte_url: string;
  } | null;
  campanha: {
    receitas_total: number;
    despesas_total: number;
    receitas_por_origem: { nome: string; valor: number }[];
    numero_doadores: number;
    fonte_url: string;
  } | null;
  /** Nulo: a candidatura não está ligada a uma pessoa por dado seguro (não é "nenhum"). */
  carreira: { ano: number; cargo: string; unidade: string; partido: string | null; situacao: string | null; eleito: boolean }[] | null;
  sancoes: {
    data: string | null;
    tipo: string;
    descricao: string;
    orgao: string | null;
    situacao: string | null;
    fonte_url: string | null;
  }[] | null;
  pessoa_id: number | null;
  perfil: string;
};

export type DisputaSegundoTurno = {
  chave: string;
  cargo: string;
  unidade: string;
  uf: string | null;
  candidatos: CandidatoSegundoTurno[];
  faltam: number;
  /** O TSE já publicou o resultado do 2º turno desta disputa. */
  decidida: boolean;
};

export type SegundoTurno = {
  localizacao: Representantes["localizacao"];
  ano_eleicao: number | null;
  data_segundo_turno: string | null;
  em_andamento: boolean;
  disputas: DisputaSegundoTurno[];
  governador_eleito_1turno: { id: number; nome_urna: string; partido: string | null; numero: string | null; perfil?: string | null } | null;
  propostas_url: string;
  fonte_nome: string;
  fonte_url: string;
  contas_url: string;
  atualizado_em: string | null;
  sancoes_fonte_nome: string;
  sancoes_fonte_url: string;
  sancoes_atualizado_em: string | null;
};

export function getSegundoTurno(busca: { cep?: string; uf?: string; municipio?: string }) {
  const params = new URLSearchParams();
  if (busca.municipio) params.set("municipio", busca.municipio);
  else if (busca.cep) params.set("cep", busca.cep);
  else if (busca.uf) params.set("uf", busca.uf);
  return getJson<SegundoTurno>(`/segundo-turno?${params}`);
}

export type AgendaSegundoTurno = {
  ano_eleicao: number | null;
  data_segundo_turno: string | null;
  em_andamento: boolean;
  presidente: boolean;
  ufs_governador: string[];
};

export function getAgendaSegundoTurno() {
  return getJson<AgendaSegundoTurno>("/segundo-turno/agenda");
}

// Explicador de votação (GET /votacoes/{casa}/{id_externo}).
export type PartidoNaVotacao = {
  partido: string;
  parlamentares: number;
  sim: number;
  nao: number;
  abstencao: number;
  obstrucao: number;
  outros: number;
  votos_efetivos: number;
  orientacao: string | null;
  /** Bloco ou federação de onde veio a orientação (nome como a fonte publica). */
  orientacao_por: string | null;
  seguiram: number | null;
};

export type ParlamentarNaVotacao = {
  parlamentar_id: number;
  nome: string;
  partido: string;
  uf: string;
  voto: string;
  /** O voto ou, quando não é voto, o registro em linguagem do dia a dia. */
  registro: string;
  efetivo: boolean;
};

export type VotacaoDetalhe = {
  casa: Casa;
  id_externo: string;
  data: string;
  descricao: string;
  proposicao: string | null;
  proposicao_ementa: string | null;
  proposicao_url: string | null;
  proposicao_id_externo?: string | null;
  temas: string[];
  secreta: boolean;
  resultado: "aprovada" | "rejeitada" | null;
  placar: { sim: number; nao: number; abstencao: number; obstrucao: number };
  outros_registros: { rotulo: string; quantidade: number }[];
  placar_oficial: { sim: number | null; nao: number | null; abstencao: number | null } | null;
  registros: number;
  cadeiras: number;
  liderancas: { bancada: string; orientacao: string | null }[];
  outras_bancadas: { bancada: string; tipo: string; orientacao: string; partidos: string[] }[];
  seguiram_governo: Placar;
  seguiram_partido: Placar;
  partidos: PartidoNaVotacao[];
  parlamentares: ParlamentarNaVotacao[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
  /** Campos acrescentados em 21/10/2026; podem faltar em respostas antigas. */
  por_uf?: PorUf[] | null;
  discursos?: DiscursosDaVotacao | null;
};

export type PorUf = { uf: string; sim: number; nao: number; outros: number; total: number };

export type DiscursoNaVotacao = {
  parlamentar_id: number;
  nome: string;
  partido: string | null;
  uf: string | null;
  data: string;
  data_hora: string | null;
  fase: string | null;
  tipo: string | null;
  /** Resumo publicado pela própria Casa; nunca interpretamos o texto. */
  sumario: string | null;
  url_texto: string | null;
  url_video: string | null;
};

export type GrupoDiscursos = {
  chave: "sim" | "nao" | "outro" | "sem_voto" | string;
  rotulo: string;
  quantidade: number;
  discursos: DiscursoNaVotacao[];
};

export type DiscursosDaVotacao = {
  total: number;
  grupos: GrupoDiscursos[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getVotacao(casa: string, id: string) {
  return getJson<VotacaoDetalhe>(`/votacoes/${encodeURIComponent(casa)}/${encodeURIComponent(id)}`);
}

// ---- Executivo: painel do ente, contas do estado e agenda (docs/DECISOES.md, 19/10/2026) ----

export type BlocoPainel = {
  disponivel: boolean;
  motivo: string | null;
  dados: Record<string, unknown> | null;
  rota: string | null;
  fonte_nome: string | null;
  fonte_url: string | null;
  atualizado_em: string | null;
};

export type PainelExecutivo = {
  candidatura_id: number;
  cargo: string;
  titular: boolean;
  nome_urna: string;
  ano_eleicao: number;
  ente: { tipo: "uniao" | "estado" | "municipio"; nome: string; uf: string | null; municipio_ibge: string | null };
  pessoa_id: number | null;
  contas: BlocoPainel;
  emendas: BlocoPainel;
  contratos: BlocoPainel;
  agenda: BlocoPainel;
  viagens_cartao: BlocoPainel;
  medidas_provisorias: BlocoPainel;
};

export function getPainelExecutivo(candidaturaId: string | number) {
  return getJson<PainelExecutivo>(`/executivo/${encodeURIComponent(String(candidaturaId))}/painel`);
}

export type ContasEstado = {
  uf: string;
  ano: number;
  populacao: number | null;
  receita_total: number | null;
  despesa_paga: number | null;
  receita_por_habitante: number | null;
  despesa_por_habitante: number | null;
  media_estados_receita_por_habitante: number | null;
  media_estados_despesa_por_habitante: number | null;
  estados_na_media: number;
  estados_sem_dado: number;
  media_estados_descricao: string;
  assembleia: number | null;
  por_area: { nome: string; valor: number; percentual: number }[];
  anterior: { ano: number; despesa_paga: number | null; receita_total: number | null } | null;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getContasEstado(uf: string) {
  return getJson<ContasEstado>(`/estados/${encodeURIComponent(uf)}/contas`);
}

export type AgendaItem = {
  tipo: string;
  rotulo: string;
  id_registro: number;
  cargo: string | null;
  orgao: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  hora_inicio: string | null;
  hora_fim: string | null;
  forma: string | null;
  assunto: string | null;
  local: string | null;
  origem: string | null;
  destino: string | null;
  detalhes: string | null;
  participantes_publicos: { nome: string; cargo: string | null; orgao: string | null }[];
  n_participantes_publicos: number;
  entidades_privadas: string[];
  n_participantes_privados: number;
  url: string;
};

export type Agenda = {
  candidatura_id: number;
  pessoa_id: number | null;
  total: number;
  pagina: number;
  por_pagina: number;
  itens: AgendaItem[];
  nota: string;
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export function getAgenda(candidaturaId: string | number, filtro: { tipo?: string; ano?: string; pagina?: string } = {}) {
  const params = new URLSearchParams();
  if (filtro.tipo) params.set("tipo", filtro.tipo);
  if (filtro.ano) params.set("ano", filtro.ano);
  if (filtro.pagina) params.set("pagina", filtro.pagina);
  const q = params.toString();
  return getJson<Agenda>(`/executivo/${encodeURIComponent(String(candidaturaId))}/agenda${q ? `?${q}` : ""}`);
}

// --- Cobertura: o que existe e o que falta, por casa e seção ---
export type CoberturaContagem = {
  sim: number;
  parcial: number;
  bloqueado: number;
  pedido: number;
  sem_fonte: number;
  total: number;
};
export type CoberturaPedido = { arquivo: string; orgao: string; data: string | null; url: string };
export type CoberturaSecao = {
  secao: string;
  situacao: "sim" | "parcial" | "bloqueado" | "pedido" | "sem_fonte";
  motivo: string;
  fonte: string;
  pedidos: CoberturaPedido[];
};
export type CoberturaCasa = { casa: string; cargo: string; secoes: CoberturaSecao[] };
export type Cobertura = {
  ufs: string[];
  uf: string | null;
  nacional: CoberturaContagem;
  resumo_uf: CoberturaContagem | null;
  casas: CoberturaCasa[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string;
};

export function getCobertura(uf?: string) {
  return getJson<Cobertura>(`/cobertura${uf ? `?uf=${encodeURIComponent(uf)}` : ""}`);
}

// --- Dinheiro federal: arrecadação da União e repasses a estados e cidades ---
export type DinheiroFederalFonte = { nome: string; url: string; atualizado_em: string | null };

/** Chaves dos blocos de repasse (FPE, FPM...) para o valor somado no ano, ou null sem dado. */
export type DinheiroFederalBlocos = Record<string, number | null>;

export type DinheiroFederalTotais = {
  populacao: number | null;
  populacao_ano: number | null;
  /** "censo" ou "estimativa". */
  populacao_origem: string | null;
  arrecadacao: number | null;
  previdencia: number | null;
  repasse: number | null;
  blocos: DinheiroFederalBlocos;
  blocos_sem_dado: string[];
};

export type DinheiroFederalAno = {
  ano: number;
  anos_disponiveis: number[];
  meses_com_dado: number[];
  ano_em_curso: boolean;
  avisos: string[];
  /** Sem arrecadação nem repasse carregados para o ano (a carga ainda não terminou). */
  sem_dados?: boolean;
};

export type DinheiroFederalUF = DinheiroFederalTotais & { uf: string; nome: string; regiao: string };

export type DinheiroFederalPainel = DinheiroFederalAno & {
  /** `sem_estado`: parte do repasse sem estado definido na fonte (está no total, em nenhum estado). */
  brasil: DinheiroFederalTotais & { sem_estado: number | null };
  ufs: DinheiroFederalUF[];
  fontes: DinheiroFederalFonte[];
};

export type DinheiroFederalCidade = {
  ibge: string;
  nome: string;
  populacao: number | null;
  repasse: number | null;
  fpm: number | null;
  outros: number | null;
};

export type DinheiroFederalEstado = DinheiroFederalAno &
  DinheiroFederalUF & {
    cidades: DinheiroFederalCidade[];
    media_estado_por_habitante: number | null;
    fontes: DinheiroFederalFonte[];
  };

export type DinheiroFederalMunicipioId = { ibge: string; nome: string; uf: string };

export type DinheiroFederalSerieAno = {
  ano: number;
  repasse: number;
  fpm: number;
  outros: number;
  populacao: number | null;
  por_habitante: number | null;
  media_estado_por_habitante: number | null;
};

export type DinheiroFederalContas = {
  ano: number;
  receita_total: number;
  receita_propria: number | null;
  transf_uniao: number | null;
  /** Percentual (0 a 100) da receita total. */
  parte_uniao: number | null;
  parte_propria: number | null;
};

export type DinheiroFederalMunicipio = {
  municipio: DinheiroFederalMunicipioId;
  serie: DinheiroFederalSerieAno[];
  contas: DinheiroFederalContas | null;
  sem_dados?: boolean;
  fontes: DinheiroFederalFonte[];
};

export function getDinheiroFederal(ano?: number) {
  return getJson<DinheiroFederalPainel>(`/dinheiro-federal${ano ? `?ano=${ano}` : ""}`);
}

export function getDinheiroFederalUf(uf: string, ano?: number) {
  return getJson<DinheiroFederalEstado>(
    `/dinheiro-federal/${encodeURIComponent(uf)}${ano ? `?ano=${ano}` : ""}`,
  );
}

export function getDinheiroFederalMunicipio(ibge: string) {
  return getJson<DinheiroFederalMunicipio>(`/municipios/${encodeURIComponent(ibge)}/dinheiro-federal`);
}

// ---- Projetos e votações (docs/DECISOES.md, 21/10/2026) ----

export type FonteBloco = { fonte_nome: string; fonte_url: string; atualizado_em: string | null };

export type CasaProjeto = "camara" | "senado" | "assembleia" | "camara_municipal";

export type UltimaVotacaoItem = {
  data: string | null;
  resultado: string | null;
  sim: number | null;
  nao: number | null;
  descricao: string | null;
  link: string;
};

export type ItemProjeto = {
  tipo: "proposicao" | "votacao_local" | "projeto_local";
  rotulo: string;
  ementa: string | null;
  esfera: "federal" | "estadual" | "municipal";
  casa: CasaProjeto;
  uf: string | null;
  municipio_ibge: string | null;
  municipio: string | null;
  situacao: string | null;
  virou_lei: boolean | null;
  ultima_votacao: UltimaVotacaoItem | null;
  na_pauta: string | null;
  ultima_movimentacao: string | null;
  link: string;
  /** Quantos itens de informação o projeto tem publicados (votação, discursos, caminho, situação, tema). */
  nivel_informacao?: number | null;
  /** Só no Congresso: discursos ligados ao projeto e passos do caminho. */
  discursos?: number | null;
  passos_caminho?: number | null;
};

/** Só com filtro de estado ou cidade: se há dado da câmara e da assembleia aqui. */
export type CoberturaBusca = {
  uf: string | null;
  camara: { municipio_ibge: string; municipio: string; tem_dados: boolean; canal_url: string | null } | null;
  assembleia: { uf: string; tem_dados: boolean } | null;
};

export type BuscaProjetos = {
  q: string | null;
  total: number;
  pagina: number;
  por_pagina: number;
  itens: ItemProjeto[];
  fontes: FonteBloco[];
  ordem?: "informacao" | "recentes";
  cobertura?: CoberturaBusca | null;
};

export type FiltrosProjetos = {
  q?: string;
  esfera?: string;
  casa?: string;
  uf?: string;
  municipio?: string;
  tema?: string;
  ano?: string;
  votacao?: string;
  ordem?: string;
  pagina?: string;
};

export function buscarProjetos(filtros: FiltrosProjetos) {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(filtros)) if (valor) params.set(chave, valor);
  return getJson<BuscaProjetos>(`/projetos?${params}`);
}

/** Temas dos projetos do Congresso (GET /projetos/temas), para o filtro de /projetos. */
export function getTemasProjetos(casa?: string) {
  const params = new URLSearchParams();
  if (casa === "camara" || casa === "senado") params.set("casa", casa);
  return getJson<{ casa: string | null; temas: string[] }>(`/projetos/temas?${params}`);
}

/** Projetos do Congresso com votação nominal, só casa, id e data (GET /projetos/ids), para o sitemap. */
export function getIdsProjetos(limite = 5000) {
  return getJson<{ itens: { casa: string; id_externo: string; data: string }[] }>(
    `/projetos/ids?votacao=com&limite=${limite}`,
  );
}

export type AutorProjeto = {
  parlamentar_id: number;
  nome: string;
  partido: string | null;
  uf: string;
  primeiro_autor: boolean;
};

export type FichaProjeto = FonteBloco & {
  temas: string[];
  autores: AutorProjeto[];
  autor_descricao: string | null;
  situacao: string | null;
  virou_lei: boolean | null;
  relator: string | null;
  relator_parlamentar_id: number | null;
  url_oficial: string | null;
  origem: string | null;
  data_apresentacao: string | null;
};

export type VotacaoDoProjeto = {
  id_externo: string;
  data: string;
  descricao: string;
  resultado: string | null;
  secreta: boolean;
  placar_publicado: { sim: number | null; nao: number | null; abstencao: number | null } | null;
  placar_contado: { sim: number; nao: number; abstencao: number; obstrucao: number; outros: number };
  link: string;
};

export type BlocoVotacoes = FonteBloco & { itens: VotacaoDoProjeto[]; aviso: string | null };

export type PessoaQueVotou = {
  parlamentar_id: number;
  nome: string;
  partido: string;
  uf: string;
  registro: string;
};

export type GrupoQuemVotou = {
  chave: "sim" | "nao" | "outros" | string;
  rotulo: string;
  quantidade: number;
  partidos: { partido: string; quantidade: number }[];
  pessoas: PessoaQueVotou[];
};

export type BlocoQuemVotou = FonteBloco & {
  votacao: VotacaoDoProjeto;
  regra: string;
  grupos: GrupoQuemVotou[];
  por_uf: PorUf[];
};

export type DiaDeDiscursos = {
  data: string;
  votacao_id_externo: string | null;
  total: number;
  grupos: GrupoDiscursos[];
};

export type BlocoDiscursos = FonteBloco & { dias: DiaDeDiscursos[]; aviso: string };

export type PassoDoCaminho = { data: string; orgao: string | null; descricao: string; etapa: string };

export type ProjetoFederal = {
  casa: Casa;
  id_externo: string;
  rotulo: string;
  sigla: string | null;
  numero: number | null;
  ano: number | null;
  ementa: string | null;
  ficha: FichaProjeto;
  votacoes: BlocoVotacoes;
  votacao_principal: BlocoQuemVotou | null;
  discursos: BlocoDiscursos;
  discursos_do_dia: FonteBloco & { quantidade_nao_atribuida: number; itens: unknown[]; aviso: string };
  caminho: FonteBloco & { itens: PassoDoCaminho[] };
  pauta: FonteBloco & { proxima: { data: string; sessao: string; url: string | null } | null };
};

export function getProjetoFederal(casa: string, id: string) {
  return getJson<ProjetoFederal>(`/projetos/${encodeURIComponent(casa)}/${encodeURIComponent(id)}`);
}

export type VotacaoLocalResumo = {
  id: number;
  data: string | null;
  materia: string;
  resultado: string | null;
  sim: number;
  nao: number;
  abstencoes: number;
  link: string;
};

export type ProjetoLocal = FonteBloco & {
  id: number;
  rotulo: string;
  tipo: string;
  numero: number | null;
  ano: number;
  ementa: string;
  data_apresentacao: string | null;
  em_tramitacao: boolean | null;
  casa: CasaProjeto;
  uf: string | null;
  municipio_ibge: string | null;
  municipio: string | null;
  autor: { mandato_id: number; nome: string; partido: string | null } | null;
  votacoes: VotacaoLocalResumo[];
  url_oficial: string;
  sem_orientacao: boolean;
  sem_discursos: boolean;
  aviso: string;
};

export function getProjetoLocal(id: string) {
  return getJson<ProjetoLocal>(`/projetos/local/${encodeURIComponent(id)}`);
}

export type VotacaoLocal = FonteBloco & {
  id: number;
  casa: CasaProjeto;
  uf: string;
  municipio_ibge: string | null;
  municipio: string | null;
  data: string | null;
  materia: string;
  ementa: string | null;
  resultado: string | null;
  sim: number;
  nao: number;
  abstencoes: number;
  votos: { mandato_id: number; nome: string; partido: string | null; voto: string }[];
  projeto_local_id: number | null;
  projeto_link: string | null;
  url_oficial: string | null;
  sem_orientacao: boolean;
  sem_discursos: boolean;
  aviso: string;
};

export function getVotacaoLocal(id: string) {
  return getJson<VotacaoLocal>(`/votacoes/local/${encodeURIComponent(id)}`);
}

export type ItemDePauta = {
  casa: Casa;
  data: string;
  sessao: string;
  ordem: number | null;
  proposicao: string | null;
  proposicao_id_externo: string | null;
  ementa: string | null;
  url_oficial: string | null;
  link: string | null;
};

export type Pauta = FonteBloco & { casa: Casa | null; dias: number; itens: ItemDePauta[]; aviso: string | null };

export function getPauta(dias = 14, casa?: Casa) {
  const params = new URLSearchParams({ dias: String(dias) });
  if (casa) params.set("casa", casa);
  return getJson<Pauta>(`/pauta?${params}`);
}

// ---------- Registro do Argos (só POST; nunca lança erro) ----------

type MensagemArgos = { autor: "cidadao" | "argos"; texto: string };

async function postarArgos(caminho: string, corpo: unknown): Promise<void> {
  try {
    await fetch(`${API_URL}${caminho}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      keepalive: true,
    });
  } catch {
    // O chat nunca quebra por causa do registro (reserva sem a rota, rede, limite de pedidos).
  }
}

/** Frase que o Argos não entendeu. O texto já deve ter passado por `limpar` (lib/argos/limpar.ts). */
export function postArgosNaoEntendida(texto: string): Promise<void> {
  return postarArgos("/argos/nao-entendida", { texto });
}

/** Avaliação "isso ajudou?"; `conversa` só vai se a pessoa deixou guardar (já limpa). */
export function postArgosAvaliacao(util: boolean, assunto: string, conversa?: MensagemArgos[]): Promise<void> {
  return postarArgos("/argos/avaliacao", { util, assunto, ...(conversa?.length ? { conversa } : {}) });
}
