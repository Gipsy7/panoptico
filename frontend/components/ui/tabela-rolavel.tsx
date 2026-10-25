"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Contêiner de tabela larga: rola na horizontal dentro de si (nunca no corpo da página) e mostra
 * um degradê à direita enquanto houver mais conteúdo. `larguraMinima` define o min-width da
 * tabela (ex.: "40rem"). Com `primeiraColunaFixa`, a primeira coluna (th/td) fica `sticky` à
 * esquerda, com fundo opaco e fio à direita.
 */
export function TabelaRolavel({
  children,
  larguraMinima = "40rem",
  primeiraColunaFixa = false,
  rotulo = "Tabela com rolagem lateral",
  className,
}: {
  children: React.ReactNode;
  larguraMinima?: string;
  primeiraColunaFixa?: boolean;
  rotulo?: string;
  className?: string;
}) {
  const rolagem = useRef<HTMLDivElement>(null);
  const [temMais, setTemMais] = useState(false);

  const medir = useCallback(() => {
    const el = rolagem.current;
    if (!el) return;
    setTemMais(el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
  }, []);

  useEffect(() => {
    medir();
    const el = rolagem.current;
    if (!el) return;
    const obs = new ResizeObserver(medir);
    obs.observe(el);
    if (el.firstElementChild) obs.observe(el.firstElementChild);
    return () => obs.disconnect();
  }, [medir]);

  return (
    <div className={cn("relative min-w-0 max-w-full", className)}>
      <div
        ref={rolagem}
        onScroll={medir}
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- região rolável precisa de foco para rolar com o teclado
        tabIndex={0}
        role="region"
        aria-label={rotulo}
        className={cn(
          "overflow-x-auto focus-visible:outline-2 focus-visible:outline-bronze",
          primeiraColunaFixa && "tabela-fixa",
        )}
      >
        <div style={{ minWidth: larguraMinima }}>{children}</div>
      </div>
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-background to-transparent transition-opacity duration-200",
          temMais ? "opacity-100" : "opacity-0",
        )}
      />
    </div>
  );
}
