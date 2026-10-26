import type { Metadata } from "next";

/** Regras de busca e de robôs que não dependem do Next: ficam aqui para ter teste. */

/** Robôs de IA de pesquisa e de treino das grandes IAs: liberados, para o Panóptico poder ser citado. */
export const ROBOS_DE_IA_LIBERADOS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "Claude-SearchBot",
  "Claude-User",
  "anthropic-ai",
  "PerplexityBot",
  "Google-Extended",
  "Applebot-Extended",
];

/** Coletores que só gastam CPU (o meta-externalagent esgotou o plano em out/2026) ou revendem dados. */
export const ROBOS_BLOQUEADOS = [
  "meta-externalagent",
  "Bytespider",
  "CCBot",
  "Amazonbot",
  "cohere-ai",
  "Diffbot",
  "PetalBot",
  "AhrefsBot",
  "SemrushBot",
  "MJ12bot",
  "DataForSeoBot",
];

/** Imagens de compartilhamento e resultado de busca por CEP: não são páginas para ler. */
export const CAMINHOS_FORA_DO_ROBOTS = ["/segundo-turno/imagem", "/comparar/imagem", "/*/opengraph-image"];

type Busca = { cep?: string; uf?: string; municipio?: string };

const IBGE = /^\d{7}$/;
const UF = /^[A-Za-z]{2}$/;

/**
 * Endereço canônico da página de representantes: só os parâmetros que definem o conteúdo, em ordem
 * fixa (`uf`, depois `municipio`). Cidade vale mais que estado; sem nenhum dos dois, a página base.
 * `ufDaCidade` vem da resposta da API (o CEP e o código do IBGE levam à cidade e ao estado).
 */
export function caminhoRepresentantes({ uf, municipio }: Busca, ufDaCidade?: string | null): string {
  const m = municipio && IBGE.test(municipio) ? municipio : undefined;
  const sigla = (ufDaCidade ?? uf)?.toUpperCase();
  const siglaValida = sigla && UF.test(sigla) ? sigla : undefined;
  if (m && siglaValida) return `/representantes?uf=${siglaValida}&municipio=${m}`;
  if (m) return `/representantes?municipio=${m}`;
  if (siglaValida) return `/representantes?uf=${siglaValida}`;
  return "/representantes";
}

/** Verdadeiro se a lista tem algum filtro, e portanto não deve ser indexada (a base aponta para ela). */
export function temFiltro(sp: Record<string, string | string[] | undefined>, ignorar: string[] = []): boolean {
  return Object.entries(sp).some(([k, v]) => !ignorar.includes(k) && (Array.isArray(v) ? v.length > 0 : Boolean(v)));
}

/**
 * Metadados de lista ou comparação com filtros na URL: a canônica é a página base e, havendo filtro, a
 * variante não entra no índice (o Google ainda segue os links dela até os perfis).
 */
export function metadadosComFiltro(
  base: string,
  sp: Record<string, string | string[] | undefined>,
  ignorar: string[] = [],
): Pick<Metadata, "alternates" | "robots"> {
  return {
    alternates: { canonical: base },
    ...(temFiltro(sp, ignorar) ? { robots: { index: false, follow: true } } : {}),
  };
}
