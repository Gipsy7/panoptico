/** Endereço público do site, usado em links de compartilhamento e no Open Graph. */
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/** E-mail do projeto, no rodapé e na página de privacidade. */
export const CONTATO_EMAIL = process.env.NEXT_PUBLIC_CONTATO_EMAIL || "contato@panoptico.social.br";

/** Endereço do site oficial (produção). */
export const SITE_OFICIAL = "https://panoptico.social.br";

export type Ambiente = "producao" | "release";

/** Lê o ambiente do build: só "release" (homologação) muda algo; qualquer outro valor é produção. */
export function lerAmbiente(valor: string | undefined): Ambiente {
  return valor?.trim().toLowerCase() === "release" ? "release" : "producao";
}

/**
 * Base dos endereços canônicos e do Open Graph. No release ela é o site oficial: se alguma página
 * de teste escapar para um buscador ou for compartilhada, o sinal aponta para a produção.
 */
export function baseCanonica(ambiente: Ambiente, siteUrl: string): string {
  return ambiente === "release" ? SITE_OFICIAL : siteUrl;
}

/** Ambiente deste build (NEXT_PUBLIC_AMBIENTE entra no código no momento do build). */
export const AMBIENTE = lerAmbiente(process.env.NEXT_PUBLIC_AMBIENTE);
export const EH_RELEASE = AMBIENTE === "release";
export const SITE_URL_CANONICO = baseCanonica(AMBIENTE, SITE_URL);
