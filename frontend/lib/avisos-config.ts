/**
 * Chave pública VAPID do build (NEXT_PUBLIC_VAPID_PUBLICA). Vazia: o recurso fica desligado, e o botão,
 * a página /avisos e os links para ela não aparecem. É o que mantém a produção e a reserva sem avisos.
 */
export const VAPID_PUBLICA = (process.env.NEXT_PUBLIC_VAPID_PUBLICA ?? "").trim();
export const AVISOS_LIGADOS = VAPID_PUBLICA !== "";

/** Endereço público da API, chamado direto do navegador (como em lib/api.ts). */
export const API_AVISOS = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
