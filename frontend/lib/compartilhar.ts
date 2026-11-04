/** Lógica pura do botão "Compartilhar" com cartão em imagem (sem React, testável). */

export type FormatoCartao = "feed" | "stories";

/** Como o botão se comporta: "whatsapp" = só o link (sem JS ou sem suporte); "nativo" = folha do celular; "baixar" = baixa a imagem e mantém o link. */
export type ModoCompartilhar = "whatsapp" | "nativo" | "baixar";

/** Endereço da imagem do cartão (`/parlamentar/12/cartao` + formato). */
export function urlCartao(cartao: string, formato: FormatoCartao = "feed"): string {
  const base = cartao.split("?")[0];
  return `${base}?formato=${formato}`;
}

/** Nome do arquivo baixado: sem acento, minúsculo, com hífens (`maria-silva-feed.png`). */
export function nomeArquivoCartao(nome: string, formato: FormatoCartao = "feed"): string {
  const slug = nome
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${slug || "panoptico"}-${formato}.png`;
}

/** Texto enviado junto da imagem: a frase e o link do perfil. */
export function textoComLink(texto: string, url: string): string {
  return `${texto} ${url}`;
}

/** Decide o modo a partir do que o navegador sabe fazer. */
export function decidirModo(suporte: {
  compartilha: boolean;
  compartilhaArquivos: boolean;
  podeBaixar: boolean;
}): ModoCompartilhar {
  if (suporte.compartilha && suporte.compartilhaArquivos) return "nativo";
  if (suporte.podeBaixar) return "baixar";
  return "whatsapp";
}
