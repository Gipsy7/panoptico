const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
};

export type Representantes = {
  localizacao: { cep: string | null; uf: string; estado: string; municipio: string | null };
  deputados: ParlamentarResumo[];
  senadores: ParlamentarResumo[];
  atualizado_em: string | null;
};

export type Resultado<T> = { ok: true; dados: T } | { ok: false; status: number; mensagem: string };

async function getJson<T>(caminho: string): Promise<Resultado<T>> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}${caminho}`);
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

export function getRepresentantes(busca: { cep?: string; uf?: string }) {
  const params = new URLSearchParams();
  if (busca.cep) params.set("cep", busca.cep);
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

export function getProjetos(id: string) {
  return getJson<Projetos>(`/parlamentares/${encodeURIComponent(id)}/projetos`);
}
