"use client";

/**
 * Abas de tema de "Por dentro" (cidade e estado) (Retrato, Dinheiro público, Política...): régua com a cor de cada assunto
 * e um painel por vez, com a faixa da cor ao lado. Os painéis chegam prontos do servidor; sem
 * JavaScript aparecem todos, um embaixo do outro (nada fica escondido).
 */
import { type KeyboardEvent, type ReactNode, useState, useSyncExternalStore } from "react";

import type { Tema } from "@/components/painel/cartao-numero";

export type AbaTema = { id: string; rotulo: string; tema: Tema; conteudo: ReactNode };

const nada = () => () => {};

export function AbasTema({ rotulo, abas }: { rotulo: string; abas: AbaTema[] }) {
  const [ativa, setAtiva] = useState(abas[0]?.id ?? "");
  // Só esconde painéis depois de hidratar: sem JS, todos ficam visíveis.
  const comJs = useSyncExternalStore(nada, () => true, () => false);
  if (abas.length === 0) return null;

  const teclar = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = abas.findIndex((a) => a.id === ativa);
    let j = -1;
    if (e.key === "ArrowRight") j = (i + 1) % abas.length;
    else if (e.key === "ArrowLeft") j = (i - 1 + abas.length) % abas.length;
    else if (e.key === "Home") j = 0;
    else if (e.key === "End") j = abas.length - 1;
    if (j < 0) return;
    e.preventDefault();
    setAtiva(abas[j].id);
    document.getElementById(`tema-${abas[j].id}-botao`)?.focus();
  };

  return (
    <div className="flex min-w-0 flex-col">
      <div
        role="tablist"
        aria-label={rotulo}
        className="-mx-4 flex snap-x gap-1 overflow-x-auto border-b border-border px-4 [scrollbar-width:none] lg:mx-0 lg:px-0"
      >
        {abas.map((a) => {
          const sel = a.id === ativa;
          return (
            <button
              key={a.id}
              type="button"
              role="tab"
              id={`tema-${a.id}-botao`}
              aria-selected={sel}
              aria-controls={`tema-${a.id}`}
              tabIndex={sel ? 0 : -1}
              onClick={() => setAtiva(a.id)}
              onKeyDown={teclar}
              style={sel ? { borderBottomColor: `var(--tema-${a.tema})` } : undefined}
              className={`flex min-h-11 shrink-0 snap-start items-center gap-2 border-b-4 px-3 text-sm whitespace-nowrap focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bronze ${
                sel ? "font-semibold text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <span aria-hidden className="size-2.5" style={{ background: `var(--tema-${a.tema})` }} />
              {a.rotulo}
            </button>
          );
        })}
      </div>
      {abas.map((a) => (
        <div
          key={a.id}
          role="tabpanel"
          id={`tema-${a.id}`}
          aria-labelledby={`tema-${a.id}-botao`}
          hidden={comJs && a.id !== ativa}
          className="border-l-4 pt-5 pl-4 lg:pl-5"
          style={{ borderLeftColor: `var(--tema-${a.tema})` }}
        >
          {a.conteudo}
        </div>
      ))}
    </div>
  );
}
