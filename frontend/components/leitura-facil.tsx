"use client";

/**
 * Chave "Ler em linguagem simples". Liga `data-leitura="facil"` no <html>; o CSS (globals.css)
 * aumenta a letra e esconde o que está marcado com `data-detalhe` dentro de `[data-perfil]`.
 * A preferência fica no localStorage e vale para todos os perfis. Sem JavaScript a chave nem
 * aparece e a página fica completa.
 */
import { useCallback, useEffect, useSyncExternalStore } from "react";

import {
  ATRIBUTO_LEITURA,
  CHAVE_LEITURA_FACIL,
  gravarPreferencia,
  lerPreferencia,
  textoEscondido,
  VALOR_LEITURA_FACIL,
} from "@/lib/leitura-facil";

const EVENTO = "panoptico:leitura-facil";

function assinar(aviso: () => void) {
  window.addEventListener(EVENTO, aviso);
  window.addEventListener("storage", aviso);
  return () => {
    window.removeEventListener(EVENTO, aviso);
    window.removeEventListener("storage", aviso);
  };
}

function lerLigado(): boolean {
  try {
    return lerPreferencia(window.localStorage.getItem(CHAVE_LEITURA_FACIL));
  } catch {
    return document.documentElement.getAttribute(ATRIBUTO_LEITURA) === VALOR_LEITURA_FACIL;
  }
}

export function LeituraFacil() {
  const ligado = useSyncExternalStore(assinar, lerLigado, () => false);

  useEffect(() => {
    const raiz = document.documentElement;
    if (ligado) raiz.setAttribute(ATRIBUTO_LEITURA, VALOR_LEITURA_FACIL);
    else raiz.removeAttribute(ATRIBUTO_LEITURA);
    return () => raiz.removeAttribute(ATRIBUTO_LEITURA);
  }, [ligado]);

  const alternar = useCallback(() => {
    const novo = gravarPreferencia(!ligado);
    try {
      if (novo === null) window.localStorage.removeItem(CHAVE_LEITURA_FACIL);
      else window.localStorage.setItem(CHAVE_LEITURA_FACIL, novo);
    } catch {
      // Sem armazenamento: vale só nesta visita.
      if (novo === null) document.documentElement.removeAttribute(ATRIBUTO_LEITURA);
      else document.documentElement.setAttribute(ATRIBUTO_LEITURA, VALOR_LEITURA_FACIL);
    }
    window.dispatchEvent(new Event(EVENTO));
  }, [ligado]);

  return (
    <div className="leitura-facil flex flex-col gap-2">
      <button
        type="button"
        role="switch"
        aria-checked={ligado}
        onClick={alternar}
        className="flex min-h-11 w-full items-center justify-between gap-3 rounded-[var(--radius)] border border-border bg-card px-4 py-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
      >
        <span className="flex min-w-0 flex-col">
          <span className="font-medium">Ler em linguagem simples</span>
          <span className="text-sm text-muted-foreground">Esconde o detalhe e aumenta a letra</span>
        </span>
        <span
          aria-hidden
          className={`relative h-6 w-11 shrink-0 rounded-full border transition-colors motion-reduce:transition-none ${
            ligado ? "border-bronze bg-bronze" : "border-border bg-muted"
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-background transition-transform motion-reduce:transition-none ${
              ligado ? "translate-x-5" : ""
            }`}
          />
        </span>
      </button>
      <div role="status" aria-live="polite">
        {ligado && (
          <p className="rounded-[var(--radius)] border border-dashed border-border p-3 text-sm leading-relaxed">
            {textoEscondido()}
          </p>
        )}
      </div>
    </div>
  );
}
