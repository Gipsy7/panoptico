"use client";

import { useEffect } from "react";

import { CHAVE_OCULTO, EVENTO_RESTAURAR } from "@/components/argos/argos-botao";

/**
 * Em /pergunte: traz o botão do Argos de volta (mesmo que tenha clicado no "×") e o esconde
 * enquanto a página está aberta, porque o chat já está nela. Não mostra nada.
 */
export function ArgosRestaurar() {
  useEffect(() => {
    try {
      sessionStorage.removeItem(CHAVE_OCULTO);
    } catch {
      // Sem armazenamento da aba: nada a desfazer.
    }
    window.dispatchEvent(new Event(EVENTO_RESTAURAR));
    // Esconde o botão fixo só enquanto esta página está na tela (regra em globals.css).
    document.documentElement.dataset.argosPagina = "1";
    return () => {
      delete document.documentElement.dataset.argosPagina;
    };
  }, []);
  return null;
}
