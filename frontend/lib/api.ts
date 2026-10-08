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
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type Eleito = {
  id: number;
  foto?: boolean;
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

export type EleitoDetalhe = Eleito &
  Pick<CandidaturaTse, "bens" | "campanha" | "fonte_nome" | "fonte_url" | "atualizado_em"> & {
    pessoais: Pessoais | null;
    cargo: string;
    unidade: string;
    municipio_ibge: string | null;
    ano_eleicao: number;
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
};

export type Camara = {
  sapl_url: string;
  itens: VereadorItem[];
  fonte_nome: string;
  fonte_url: string;
  atualizado_em: string | null;
};

export type VereadorDetalhe = VereadorItem & {
  municipio_ibge: string;
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

export function getVereador(id: string) {
  return getJson<VereadorDetalhe>(`/vereadores/${encodeURIComponent(id)}`);
}

export type ContasMunicipio = {
  ano: number;
  populacao: number | null;
  receita_total: number | null;
  despesa_paga: number | null;
  despesa_por_habitante: number | null;
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
  outros_autores: { autor_nome: string; total: number }[];
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
