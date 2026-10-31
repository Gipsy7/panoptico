/**
 * Lógica pura da contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). Nada aqui lê o
 * navegador: quem lê (components/contagem-acessos.tsx) passa os valores. O que vai ao servidor é
 * só o caminho da página (sem query nem fragmento), a categoria da origem, o tipo de aparelho e,
 * em ações, o nome do recurso. Nunca CEP, nunca texto digitado.
 */

export type Origem = "direto" | "whatsapp" | "google" | "buscadores" | "redes" | "outro_site";
export type Dispositivo = "celular" | "computador";
export type Recurso = "cep" | "localizacao" | "argos" | "compartilhar" | "pix";

/** Chave do localStorage que tira este aparelho da contagem (ligada ao entrar no painel). */
export const CHAVE_SEM_CONTAGEM = "panoptico-sem-contagem";
/** Chave do sessionStorage que marca o início da visita; só guarda "1", sem identificador. */
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
export function tipoDeAparelho(toqueGrosso: boolean): Dispositivo {
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

export type CorpoVisita = {
  caminho: string;
  nova: boolean;
  origem?: Origem;
  dispositivo?: Dispositivo;
};

/** Monta o corpo de uma página vista. Origem e aparelho só vão no início da visita. */
export function montarVisita(
  pathname: string,
  nova: boolean,
  origem: Origem,
  dispositivo: Dispositivo,
): CorpoVisita {
  return nova ? { caminho: pathname, nova, origem, dispositivo } : { caminho: pathname, nova };
}
