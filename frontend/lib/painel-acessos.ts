/**
 * Tipos da resposta de GET /painel/resumo e lógica pura do painel privado de acessos
 * (docs/DECISOES.md, 2026-10-31). Nada aqui toca o navegador.
 */

export type Par = { atual: number; anterior: number };
export type ItemContado = { chave: string; atual: number; anterior: number };
export type PaginaContada = ItemContado & { conteudo: boolean };
export type Representante = ItemContado & { nome: string; cargo: string; uf: string | null; partido: string | null };
export type ProjetoContado = ItemContado & { rotulo: string; casa: string };
export type PontoDaSerie = {
  dia: string;
  semana: string;
  visitas: number;
  paginas_vistas: number;
  buscas_cep: number;
  compartilhamentos: number;
};
export type Cidade = { ibge: string; nome: string; uf: string; total: number };
export type DiaDaSemana = { dia: string; dias: number; media: number };

export type Resumo = {
  hoje: string;
  inicio_da_contagem: string | null;
  dias: number;
  filtros: { aparelho: string | null; origem: string | null; uf: string | null };
  tiles: { visitas: Par; paginas_vistas: Par; buscas_cep: Par; compartilhamentos: Par };
  serie: PontoDaSerie[];
  origens: ItemContado[];
  paginas: PaginaContada[];
  rotas_fixas: string[];
  representantes: Representante[];
  projetos: ProjetoContado[];
  partidos: ItemContado[];
  regioes: { chave: string; total: number }[];
  ufs: { uf: string; total: number }[];
  cidades: { itens: Cidade[]; fora: number; minimo: number };
  uso: {
    recursos: ItemContado[];
    entradas: ItemContado[];
    ultimas: ItemContado[];
    secoes: ItemContado[];
    cep: { com: number; sem: number; com_anterior: number; sem_anterior: number };
    dia_da_semana: DiaDaSemana[];
  };
  item: {
    tipo: string;
    chave: string;
    rotulo: string;
    atual: number;
    anterior: number;
    serie: { dia: string; total: number }[];
  } | null;
};

export const PERIODOS = [
  { v: 1, n: "Hoje" },
  { v: 7, n: "7 dias" },
  { v: 30, n: "30 dias" },
] as const;

export const ORIGENS: Record<string, string> = {
  direto: "Direto",
  whatsapp: "WhatsApp",
  google: "Google",
  buscadores: "Outros buscadores",
  redes: "Redes sociais",
  outro_site: "Link de outro site",
};
export const APARELHOS: Record<string, string> = { celular: "Celular ou tablet", computador: "Computador" };
export const RECURSOS: Record<string, string> = {
  cep: "Busca por CEP",
  localizacao: "Uso da localização",
  argos: "Abriu o Argos",
  compartilhar: "Compartilhou no WhatsApp",
  pix: "Copiou o Pix",
};
export const SECOES: Record<string, string> = {
  gastos: "Gastos",
  presenca: "Presença",
  projetos: "Projetos",
  votos: "Votos",
  "votos-tema": "Votos por tema",
  remuneracao: "Salário",
  sancoes: "Sanções",
  fornecedores: "Fornecedores",
  "fornecedores-pncp": "Fornecedores (contratos)",
  "contratos-socio": "Contratos de empresas de sócio",
  comissoes: "Comissões",
  carreira: "Carreira",
  canais: "Canais oficiais",
  candidatura: "Candidatura",
  temas: "Temas",
  "linha-do-tempo": "Linha do tempo",
  "servico-federal": "Servidores federais",
  "emendas-relator": "Emendas do relator",
  "destino-emendas": "Destino das emendas",
  contas: "Contas",
  executivo: "Poder Executivo",
};

const PAGINAS: Record<string, string> = {
  "/": "Página inicial",
  "/parlamentares": "Lista de parlamentares",
  "/projetos": "Projetos de lei",
  "/partidos": "Dinheiro dos partidos",
  "/partidos/[sigla]": "Um partido",
  "/impostos-e-repasses": "Impostos e repasses",
  "/impostos-e-repasses/[lugar]": "Impostos e repasses de um lugar",
  "/segundo-turno": "Segundo turno",
  "/comparar": "Comparar parlamentares",
  "/comparar/local": "Comparar cidades",
  "/sobre-as-fontes": "Sobre as fontes",
  "/sobre-as-fontes/cobertura": "Cobertura das fontes",
  "/status": "Status",
  "/privacidade": "Privacidade",
  "/acessibilidade": "Acessibilidade",
  "/apoie": "Apoie",
  "/apoiadores": "Apoiadores",
  "/o-panoptico": "O que é o Panóptico",
  "/perguntas": "Perguntas frequentes",
  "/pergunte": "Pergunte ao Argos",
  "/representantes": "Resultado da busca por representantes",
  "/avisos": "Avisos",
  "/parlamentar/[id]": "Perfil de deputado federal ou senador",
  "/cidade/[ibge]": "Página de uma cidade",
  "/eleito/[id]": "Perfil de eleito",
  "/vereador/[id]": "Perfil de vereador",
  "/deputado-estadual/[id]": "Perfil de deputado estadual",
  "/projeto/[id]": "Um projeto de lei",
  "/votacao/[id]": "Uma votação",
};

/** Nome em português de uma página; o caminho entre parênteses ajuda a achar no site. */
export function nomeDaPagina(chave: string): string {
  return PAGINAS[chave] ?? chave;
}

/** Diferença em número, em texto simples: "12 a mais que ontem", "3 a menos", "igual". */
export function textoDaDiferenca(atual: number, anterior: number, base: string): string {
  const d = atual - anterior;
  const n = Math.abs(d).toLocaleString("pt-BR");
  if (d === 0) return `igual ${base}`;
  return `${n} ${d > 0 ? "a mais" : "a menos"} ${base}`;
}

/** Diferença curta para as listas: "+12", "-3", "0". */
export function sinal(d: number): string {
  if (d === 0) return "0";
  return `${d > 0 ? "+" : "−"}${Math.abs(d).toLocaleString("pt-BR")}`;
}

/** A base de comparação dita em texto: "ontem" ou "os 7 dias anteriores". */
export function baseDeComparacao(dias: number): string {
  return dias === 1 ? "que ontem" : `que nos ${dias} dias anteriores`;
}

export function percentual(parte: number, total: number): number {
  return total > 0 ? (parte / total) * 100 : 0;
}

export function formatarPercentual(p: number): string {
  return `${Math.round(p).toLocaleString("pt-BR")}%`;
}

export type ModoDePaginas = "mais" | "menos" | "alta" | "zero";

/** Páginas na ordem pedida. "menos" e "zero" só olham páginas de conteúdo; "zero" usa as rotas fixas. */
export function ordenarPaginas(
  modo: ModoDePaginas,
  paginas: PaginaContada[],
  rotasFixas: string[],
  busca = "",
): (PaginaContada & { dif: number })[] {
  const q = busca.trim().toLowerCase();
  const casa = (p: { chave: string }) => !q || nomeDaPagina(p.chave).toLowerCase().includes(q) || p.chave.includes(q);
  const base = paginas.map((p) => ({ ...p, dif: p.atual - p.anterior })).filter(casa);
  if (modo === "mais") return base.filter((p) => p.atual > 0).sort((a, b) => b.atual - a.atual || a.chave.localeCompare(b.chave));
  if (modo === "menos") {
    return base.filter((p) => p.conteudo && p.atual > 0).sort((a, b) => a.atual - b.atual || a.chave.localeCompare(b.chave));
  }
  if (modo === "alta") return base.filter((p) => p.dif > 0).sort((a, b) => b.dif - a.dif || a.chave.localeCompare(b.chave));
  const porChave = new Map(paginas.map((p) => [p.chave, p]));
  return rotasFixas
    .filter((c) => (porChave.get(c)?.atual ?? 0) === 0)
    .map((c) => ({ chave: c, atual: 0, anterior: porChave.get(c)?.anterior ?? 0, conteudo: true, dif: -(porChave.get(c)?.anterior ?? 0) }))
    .filter(casa);
}

/** Cargos que aparecem nos dados, na ordem de mais para menos abertos. */
export function cargosPresentes(reps: Representante[]): string[] {
  const soma = new Map<string, number>();
  for (const r of reps) soma.set(r.cargo, (soma.get(r.cargo) ?? 0) + r.atual);
  return [...soma.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
}

export function filtrarRepresentantes(reps: Representante[], cargo: string, uf: string): Representante[] {
  return reps
    .filter((r) => (cargo === "todos" || r.cargo === cargo) && (uf === "todas" || r.uf === uf))
    .sort((a, b) => b.atual - a.atual || a.nome.localeCompare(b.nome, "pt-BR"));
}

/** Posição de cada UF no mapa em grade (coluna, linha). */
export const GRADE_UFS: Record<string, [number, number]> = {
  RR: [2, 0], AP: [3, 0],
  AM: [1, 1], PA: [2, 1], MA: [3, 1], CE: [4, 1], RN: [5, 1],
  AC: [0, 2], RO: [1, 2], TO: [2, 2], PI: [3, 2], PE: [4, 2], PB: [5, 2],
  MT: [1, 3], GO: [2, 3], BA: [3, 3], AL: [4, 3], SE: [5, 3],
  MS: [1, 4], DF: [2, 4], MG: [3, 4], ES: [4, 4],
  SP: [2, 5], RJ: [3, 5],
  PR: [2, 6], SC: [3, 6],
  RS: [2, 7],
};

export const NOMES_UF: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul",
  MG: "Minas Gerais", PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima",
  SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
};

/** Faixa de 0 (nenhuma busca) a 4 (a maior), em quartos do maior valor. Só para a cor do mapa. */
export function faixaDoMapa(total: number, maior: number): 0 | 1 | 2 | 3 | 4 {
  if (total <= 0 || maior <= 0) return 0;
  const r = total / maior;
  return r > 0.75 ? 4 : r > 0.5 ? 3 : r > 0.25 ? 2 : 1;
}

/** Classes (tema claro e escuro) de cada faixa: bronze misturado ao fundo do cartão. */
export const COR_DA_FAIXA = [
  "bg-card ring-1 ring-inset ring-border",
  "bg-[color-mix(in_srgb,var(--bronze)_18%,var(--card))] dark:bg-[color-mix(in_srgb,var(--bronze)_11%,var(--card))]",
  "bg-[color-mix(in_srgb,var(--bronze)_36%,var(--card))] dark:bg-[color-mix(in_srgb,var(--bronze)_22%,var(--card))]",
  "bg-[color-mix(in_srgb,var(--bronze)_54%,var(--card))] dark:bg-[color-mix(in_srgb,var(--bronze)_34%,var(--card))]",
  "bg-[color-mix(in_srgb,var(--bronze)_72%,var(--card))] dark:bg-[color-mix(in_srgb,var(--bronze)_45%,var(--card))]",
] as const;

/** "28/10" a partir de "2026-10-28". */
export function diaCurto(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

/** Máximo "redondo" para o eixo e passo de 4 divisões. */
export function escalaDoEixo(maximo: number): { topo: number; passo: number } {
  if (maximo <= 4) return { topo: 4, passo: 1 };
  const bruto = maximo / 4;
  const pot = 10 ** Math.floor(Math.log10(bruto));
  const passo = ([1, 2, 2.5, 5, 10].map((m) => m * pot).find((p) => p >= bruto) ?? pot * 10);
  return { topo: Math.ceil(maximo / passo) * passo, passo };
}

/** Melhor dia da semana pela média por dia; null se nenhum dia teve visita. */
export function diaDeMaiorMedia(dias: DiaDaSemana[]): DiaDaSemana | null {
  const c = dias.filter((d) => d.dias > 0).sort((a, b) => b.media - a.media);
  return c[0] && c[0].media > 0 ? c[0] : null;
}
