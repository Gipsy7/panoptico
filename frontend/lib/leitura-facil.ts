/**
 * Leitura fácil: lógica pura do modo "Ler em linguagem simples". A página é a mesma; com o
 * modo ligado a letra cresce e o detalhe (marcado com `data-detalhe`) some, enquanto o resumo,
 * os números principais com a média da Casa e a fonte com a data continuam à vista.
 * A preferência fica só neste aparelho (localStorage) e vale para todos os perfis.
 */

export const CHAVE_LEITURA_FACIL = "panoptico:leitura-facil";
export const ATRIBUTO_LEITURA = "data-leitura";
export const VALOR_LEITURA_FACIL = "facil";

/** O que o modo esconde, na ordem em que aparece na página. Alimenta o quadro "Escondemos". */
export const ESCONDIDO_NA_LEITURA_FACIL = [
  "as abas de detalhe (gastos por tipo, votos um a um, lista de projetos, emendas, comissões e carreira)",
  "a lista do que o perfil tem e do que falta",
  "as perguntas e respostas sobre os números",
  "os atalhos para comparar e para ver outros representantes",
] as const;

export function lerPreferencia(valor: string | null | undefined): boolean {
  return valor === "1";
}

export function gravarPreferencia(ligado: boolean): string | null {
  return ligado ? "1" : null;
}

export function juntar(itens: readonly string[]): string {
  if (itens.length <= 1) return itens.join("");
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}

/** Texto do quadro que diz o que foi escondido. */
export function textoEscondido(itens: readonly string[] = ESCONDIDO_NA_LEITURA_FACIL): string {
  return `Escondemos ${juntar(itens)}. Desligue a chave para ver tudo.`;
}
