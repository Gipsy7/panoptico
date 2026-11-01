/**
 * Lógica pura da contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). Nada aqui lê o
 * navegador: quem lê (components/contagem-acessos.tsx) passa os valores. O que vai ao servidor é
 * só o caminho da página (sem query nem fragmento), a categoria da origem, o tipo de aparelho e,
 * em ações, o nome do recurso. Nunca CEP, nunca texto digitado.
 */

export type Origem = "direto" | "whatsapp" | "google" | "buscadores" | "redes" | "outro_site";
export type Aparelho = "celular" | "computador";
export type Recurso = "cep" | "localizacao" | "argos" | "compartilhar" | "pix";
export type FormaDeBusca = "cep" | "cidade" | "estado";

export const ORIGENS: readonly Origem[] = ["direto", "whatsapp", "google", "buscadores", "redes", "outro_site"];

/** Seções do perfil (ids dos títulos `<h2 id="gastos-titulo">`) que a contagem reconhece. */
export const SECOES = [
  "gastos", "presenca", "projetos", "votos", "votos-tema", "remuneracao", "sancoes", "fornecedores",
  "fornecedores-pncp", "contratos-socio", "comissoes", "carreira", "canais", "candidatura", "temas",
  "linha-do-tempo", "servico-federal", "emendas-relator", "destino-emendas", "contas", "executivo",
] as const;
export type Secao = (typeof SECOES)[number];

/** Chave do localStorage que tira este aparelho da contagem (ligada ao entrar no painel). */
export const CHAVE_SEM_CONTAGEM = "panoptico-sem-contagem";
/**
 * Chave do sessionStorage que marca o início da visita. Guarda só a categoria da origem
 * (ex.: "google"), a mesma para todos que vêm dali: não identifica ninguém.
 */
export const CHAVE_VISITA = "panoptico-visita";

const WHATSAPP = ["wa.me", "whatsapp.com"];
const BUSCADORES = ["bing.com", "duckduckgo.com", "yahoo.com", "ecosia.org", "yandex.com", "yandex.ru", "brave.com", "baidu.com", "startpage.com"];
const REDES = [
  "facebook.com", "fb.com", "fb.me", "instagram.com", "twitter.com", "x.com", "t.co", "youtube.com", "youtu.be",
  "linkedin.com", "lnkd.in", "tiktok.com", "t.me", "telegram.org", "reddit.com", "threads.net", "bsky.app", "kwai.com",
];

function pertence(host: string, dominios: string[]): boolean {
  return dominios.some((d) => host === d || host.endsWith(`.${d}`));
}

/** Categoriza o `document.referrer`; só a categoria sai do aparelho. */
export function categorizarOrigem(referrer: string, hostDoSite: string): Origem {
  if (!referrer) return "direto";
  let host: string;
  try {
    host = new URL(referrer).hostname.toLowerCase();
  } catch {
    return "direto";
  }
  if (!host || host === hostDoSite.toLowerCase()) return "direto";
  if (pertence(host, WHATSAPP)) return "whatsapp";
  if (/(^|\.)google\.[a-z.]+$/.test(host) || host === "goo.gl") return "google";
  if (pertence(host, BUSCADORES)) return "buscadores";
  if (pertence(host, REDES)) return "redes";
  return "outro_site";
}

/** Aparelho de toque (celular ou tablet) ou de mouse (computador). */
export function tipoDeAparelho(toqueGrosso: boolean): Aparelho {
  return toqueGrosso ? "celular" : "computador";
}

/** Caminhos que nunca entram na contagem (a área privada). */
export function caminhoContavel(pathname: string): boolean {
  return pathname.startsWith("/") && !pathname.startsWith("/painel");
}

export type SinaisDoNavegador = {
  webdriver?: boolean;
  /** "1" no `navigator.doNotTrack` ou `globalPrivacyControl` ligado. */
  naoRastrear?: boolean;
  /** Valor do localStorage em CHAVE_SEM_CONTAGEM. */
  aparelhoDoDono?: string | null;
};

/** O navegador pediu para não ser contado, é automatizado ou é o aparelho do dono. */
export function deveIgnorar(s: SinaisDoNavegador): boolean {
  return Boolean(s.webdriver || s.naoRastrear || s.aparelhoDoDono === "1");
}

/** Lê a origem guardada na sessão; qualquer valor fora da lista é descartado. */
export function origemGuardada(valor: string | null): Origem | null {
  return ORIGENS.find((o) => o === valor) ?? null;
}

/** Seção reconhecida pela âncora (`#gastos-titulo`) ou pelo id do título; senão, null. */
export function secaoDoId(id: string | null | undefined): Secao | null {
  const nome = (id ?? "").replace(/^#/, "").replace(/-titulo$/, "");
  return SECOES.find((s) => s === nome) ?? null;
}

export type Dims = { origem: Origem; aparelho: Aparelho };

export type CorpoVisita = Dims & { caminho: string; nova: boolean };

/** Corpo de uma página vista. Origem e aparelho vão em todo beacon, para o painel cruzar. */
export function montarVisita(pathname: string, nova: boolean, origem: Origem, aparelho: Aparelho): CorpoVisita {
  return { caminho: pathname, nova, origem, aparelho };
}

export type CorpoBusca = Dims & {
  forma: FormaDeBusca;
  resultado: boolean;
  uf?: string;
  ibge?: string;
};

/** Busca de representantes: só o resultado e, quando houve, o estado e a cidade (IBGE). Nunca o CEP. */
export function montarBusca(
  dims: Dims,
  forma: FormaDeBusca,
  resultado: boolean,
  uf?: string | null,
  ibge?: string | null,
): CorpoBusca {
  const corpo: CorpoBusca = { ...dims, forma, resultado };
  if (resultado && uf && /^[A-Z]{2}$/.test(uf)) corpo.uf = uf;
  if (resultado && ibge && /^\d{7}$/.test(ibge)) corpo.ibge = ibge;
  return corpo;
}
