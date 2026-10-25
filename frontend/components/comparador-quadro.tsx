"use client";

import { type ReactNode, useRef } from "react";

/**
 * Moldura do comparador: o cabeçalho (fotos e nomes) fica fixo no alto da tela e a tabela rola de
 * lado. Como um elemento com rolagem horizontal não deixa o filho ficar fixo na vertical, o
 * cabeçalho e a tabela são dois rolantes separados, com a rolagem lateral sincronizada.
 */
export function ComparadorQuadro({
  cabecalho,
  colunas,
  children,
}: {
  cabecalho: ReactNode;
  /** Número de colunas de pessoas (inclui a de "Adicionar", se houver). */
  colunas: number;
  children: ReactNode;
}) {
  const topo = useRef<HTMLDivElement>(null);
  const corpo = useRef<HTMLDivElement>(null);

  function sincronizar(origem: "topo" | "corpo") {
    const de = origem === "topo" ? topo.current : corpo.current;
    const para = origem === "topo" ? corpo.current : topo.current;
    if (de && para && para.scrollLeft !== de.scrollLeft) para.scrollLeft = de.scrollLeft;
  }

  return (
    <div className="-mx-4 md:mx-0" style={{ ["--c" as string]: colunas }}>
      <div
        ref={topo}
        onScroll={() => sincronizar("topo")}
        className="sticky top-14 z-30 snap-x snap-mandatory overflow-x-auto scroll-pl-[132px] border-b border-foreground bg-background [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        <div className="grid min-w-[calc(132px_+_var(--c)*104px)] grid-cols-[132px_repeat(var(--c),104px)] md:min-w-0 md:grid-cols-[200px_repeat(var(--c),minmax(0,1fr))]">
          {cabecalho}
        </div>
      </div>
      <div
        ref={corpo}
        onScroll={() => sincronizar("corpo")}
        role="region"
        aria-label="Tabela de comparação, role para os lados para ver todas as pessoas"
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- região rolável precisa de foco para rolar com o teclado
        tabIndex={0}
        className="snap-x snap-mandatory overflow-x-auto scroll-pl-[132px] focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-bronze"
      >
        {children}
      </div>
    </div>
  );
}
