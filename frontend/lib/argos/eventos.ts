/**
 * Pedir ao Argos (o botão flutuante) que abra já respondendo a uma frase, de qualquer lugar da
 * página, sem carregar o chat junto. O botão escuta o evento e o cancela para dizer que atendeu;
 * se ninguém atender (sem o botão na página), quem chamou segue o link para /pergunte?q=...
 */
export const EVENTO_PERGUNTAR = "argos:perguntar";

export type PedidoArgos = { frase: string };

/** Dispara o pedido; devolve `true` se o Argos da página atendeu. */
export function pedirAoArgos(frase: string): boolean {
  const evento = new CustomEvent<PedidoArgos>(EVENTO_PERGUNTAR, { detail: { frase }, cancelable: true });
  return !window.dispatchEvent(evento);
}

/** Endereço de /pergunte já com a frase (funciona sem JavaScript). */
export function enderecoPergunta(frase: string): string {
  return `/pergunte?q=${encodeURIComponent(frase)}`;
}
