"use client";

/**
 * Botão de tema: um ícone só, que alterna entre claro e escuro. Enquanto a pessoa não escolhe,
 * o site segue o sistema (prefers-color-scheme), sem atributo na raiz. Ao tocar, grava a escolha
 * no localStorage (chave "tema") e marca `data-theme` na raiz; o script do <head> em layout.tsx
 * a aplica antes da pintura nas visitas seguintes, sem piscar. O ícone mostra para onde vai:
 * lua quando está claro, sol quando está escuro.
 */
import { useSyncExternalStore } from "react";

type Tema = "light" | "dark";

const ESCURO = "(prefers-color-scheme: dark)";

function observar(aviso: () => void) {
  const o = new MutationObserver(aviso);
  o.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  const sistema = window.matchMedia(ESCURO);
  sistema.addEventListener("change", aviso);
  return () => {
    o.disconnect();
    sistema.removeEventListener("change", aviso);
  };
}

/** Tema em uso: o escolhido (atributo na raiz) ou, sem escolha, o do sistema. */
function emUso(): Tema {
  const t = document.documentElement.getAttribute("data-theme");
  if (t === "light" || t === "dark") return t;
  return window.matchMedia(ESCURO).matches ? "dark" : "light";
}

export function AlternarTema({ className = "" }: { className?: string }) {
  // No servidor não se sabe o tema: o rótulo sai neutro e se acerta na hidratação.
  const tema = useSyncExternalStore(observar, emUso, () => null);
  const proximo: Tema = tema === "dark" ? "light" : "dark";
  const rotulo = tema === null ? "Trocar entre tema claro e escuro" : proximo === "dark" ? "Usar tema escuro" : "Usar tema claro";

  function alternar() {
    document.documentElement.setAttribute("data-theme", proximo);
    try {
      localStorage.setItem("tema", proximo);
    } catch {
      // Armazenamento bloqueado: vale só nesta visita.
    }
  }

  return (
    <button
      type="button"
      onClick={alternar}
      aria-label={rotulo}
      title={rotulo}
      className={`flex size-11 shrink-0 items-center justify-center rounded-[2px] text-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze ${className}`}
    >
      {/* Antes de hidratar, o CSS escolhe o ícone pelo tema da página (classes dark:). */}
      <svg aria-hidden viewBox="0 0 24 24" className="size-6 dark:hidden" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
      </svg>
      <svg aria-hidden viewBox="0 0 24 24" className="hidden size-6 dark:block" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
      </svg>
    </button>
  );
}
