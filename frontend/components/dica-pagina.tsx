"use client";

/**
 * Dica curta no pé da tela, uma linha por página, com "Entendi". Aparece uma vez por página e
 * por aparelho (localStorage, com try/catch) e espera enquanto o guia da primeira visita está na
 * tela. Fica acima do botão fixo do Argos (embaixo, à direita), sem cobri-lo. Renderiza só no
 * cliente, depois de ler o aparelho: não empurra o conteúdo.
 */
import { useEffect, useState, useSyncExternalStore } from "react";

import {
  chaveArmazenamentoDica,
  type ChaveDica,
  dicaJaVista,
  textoDaDica,
} from "@/lib/dicas";
import { ATRIBUTO_GUIA_VISIVEL } from "@/lib/guia-visita";

function assinarGuia(aviso: () => void) {
  const observador = new MutationObserver(aviso);
  observador.observe(document.documentElement, { attributes: true, attributeFilter: [ATRIBUTO_GUIA_VISIVEL] });
  return () => observador.disconnect();
}

const guiaVisivel = () => document.documentElement.hasAttribute(ATRIBUTO_GUIA_VISIVEL);

export function DicaPagina({ chave }: { chave: ChaveDica }) {
  const texto = textoDaDica(chave);
  const [vista, setVista] = useState<boolean | null>(null);
  const guiaNaTela = useSyncExternalStore(assinarGuia, guiaVisivel, () => false);

  useEffect(() => {
    const quadro = requestAnimationFrame(() => {
      try {
        setVista(dicaJaVista(window.localStorage.getItem(chaveArmazenamentoDica(chave))));
      } catch {
        setVista(false);
      }
    });
    return () => cancelAnimationFrame(quadro);
  }, [chave]);

  if (!texto || vista !== false || guiaNaTela) return null;

  function entendi() {
    setVista(true);
    try {
      window.localStorage.setItem(chaveArmazenamentoDica(chave), "1");
    } catch {
      // Sem armazenamento: só não lembra.
    }
  }

  return (
    <aside
      aria-label="Dica desta página"
      className="fixed inset-x-2 bottom-[calc(5rem+env(safe-area-inset-bottom))] z-30 mx-auto flex max-w-xl items-center gap-2.5 rounded-md bg-primary py-2 pr-2 pl-3.5 text-primary-foreground shadow-[0_10px_24px_-8px_rgb(0_0_0/0.5)] print:hidden"
    >
      <p role="status" className="flex-1 text-sm leading-snug">
        <span className="block text-[0.6875rem] tracking-[0.12em] uppercase">Dica</span>
        {texto}
      </p>
      <button
        type="button"
        onClick={entendi}
        className="min-h-11 flex-none rounded-[2px] border border-primary-foreground px-3.5 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-foreground"
      >
        Entendi
      </button>
    </aside>
  );
}
