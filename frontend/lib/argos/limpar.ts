/**
 * Limpeza do texto antes de qualquer envio do Argos ao servidor. Mesmas regras de
 * `backend/app/services/argos.py` (o servidor limpa de novo; nunca confia no site): troca por
 * "[removido]" URL, e-mail, CPF, CEP, telefone e qualquer sequência de 5 ou mais dígitos.
 */

export const MARCA = "[removido]";
export const MAX_FRASE = 300;
export const MAX_MENSAGEM = 500;
export const MAX_MENSAGENS = 30;

// Ordem importa: padrões específicos antes do genérico "5 ou mais dígitos".
const PADROES: RegExp[] = [
  /(?:https?:\/\/|www\.)\S+/gi, // URLs
  /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g, // e-mails
  /(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)/g, // CPF
  /(?<!\d)\d{5}\s?-?\s?\d{3}(?!\d)/g, // CEP
  /(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\s?\d{4}[\s-]?\d{4}(?!\d)/g, // telefone
  /\d{5,}/g, // qualquer sequência de 5 ou mais dígitos
];

export function limpar(texto: string, limite: number = MAX_FRASE): string {
  let t = texto;
  for (const p of PADROES) t = t.replace(p, MARCA);
  return t.replace(/\s+/g, " ").trim().slice(0, limite);
}

/** Depois da limpeza não sobrou nada que sirva (só a marca e pontuação). */
export function soMarca(texto: string): boolean {
  return texto.split(MARCA).join("").replace(/[\s.,;:!?-]/g, "") === "";
}

export type MensagemRegistro = { autor: "cidadao" | "argos"; texto: string };

/** Últimas 30 mensagens, cada uma limpa e com até 500 caracteres; sem mensagem vazia. */
export function prepararConversa(mensagens: MensagemRegistro[]): MensagemRegistro[] {
  return mensagens
    .map((m) => ({ autor: m.autor, texto: limpar(m.texto, MAX_MENSAGEM) }))
    .filter((m) => m.texto.length > 0)
    .slice(-MAX_MENSAGENS);
}
