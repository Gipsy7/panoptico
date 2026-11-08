"use client";

/**
 * O lugar escolhido no cabeçalho ("Blumenau, SC") e o gancho que o lê. `LembrarLugar` grava o lugar
 * quando a pessoa abre uma cidade (página da cidade ou "Quem te representa"), sem ela precisar
 * pedir. Tudo no aparelho; sem armazenamento, o site funciona igual, só não lembra.
 */
import Link from "next/link";
import { useEffect, useSyncExternalStore } from "react";

import { CHAVE_LUGAR, EVENTO_LUGAR, type Lugar, gravarLugar, lerLugar } from "@/lib/lugar";

function assinar(aviso: () => void) {
  window.addEventListener(EVENTO_LUGAR, aviso);
  window.addEventListener("storage", aviso);
  return () => {
    window.removeEventListener(EVENTO_LUGAR, aviso);
    window.removeEventListener("storage", aviso);
  };
}

function lerBruto(): string | null {
  try {
    return window.localStorage.getItem(CHAVE_LUGAR);
  } catch {
    return null;
  }
}

export function useLugar(): Lugar | null {
  const bruto = useSyncExternalStore(assinar, lerBruto, () => null);
  return lerLugar(bruto);
}

export function LembrarLugar({ ibge, nome, uf }: Lugar) {
  useEffect(() => {
    try {
      const novo = gravarLugar({ ibge, nome, uf });
      if (window.localStorage.getItem(CHAVE_LUGAR) === novo) return;
      window.localStorage.setItem(CHAVE_LUGAR, novo);
      window.dispatchEvent(new Event(EVENTO_LUGAR));
    } catch {
      // Armazenamento bloqueado: não lembra.
    }
  }, [ibge, nome, uf]);
  return null;
}

const PINO = (
  <svg aria-hidden viewBox="0 0 24 24" className="size-4 shrink-0 text-bronze" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" />
    <circle cx="12" cy="9.5" r="2.5" />
  </svg>
);

/** O lugar no cabeçalho: com lugar, "Blumenau, SC" (leva à cidade); sem, "Escolher cidade". */
export function LugarNoCabecalho({ compacto = false }: { compacto?: boolean }) {
  const lugar = useLugar();
  return (
    <Link
      href={lugar ? `/cidade/${lugar.ibge}` : "/#cep"}
      className="inline-flex min-h-10 max-w-[11rem] items-center gap-1.5 rounded-[var(--raio)] border border-border bg-card px-2.5 text-sm whitespace-nowrap hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-bronze"
    >
      {PINO}
      <span className="truncate">{lugar ? (compacto ? lugar.nome : `${lugar.nome}, ${lugar.uf}`) : "Escolher cidade"}</span>
      {lugar && <span className="sr-only">: abrir a página da cidade</span>}
    </Link>
  );
}
