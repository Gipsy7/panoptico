"use client";

import { useEffect, useRef, useState } from "react";

export type ItemIndice = { id: string; rotulo: string };

/**
 * Índice de seções do perfil. No celular: fileira de pílulas de 44 px, rolável e fixa sob o
 * cabeçalho. No computador: lista vertical `sticky` numa coluna lateral. Destaca a seção visível
 * (IntersectionObserver) e mostra "voltar ao topo" depois de rolar. Só lista seções que existem
 * na página (algumas somem quando não há dado).
 */
export function IndicePerfil({ itens }: { itens: ItemIndice[] }) {
  const [presentes, setPresentes] = useState<ItemIndice[]>(itens);
  const [ativo, setAtivo] = useState<string | null>(null);
  const [mostrarTopo, setMostrarTopo] = useState(false);
  const fileira = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const quadro = requestAnimationFrame(() => setPresentes(itens.filter((i) => document.getElementById(i.id))));
    return () => cancelAnimationFrame(quadro);
  }, [itens]);

  useEffect(() => {
    const visiveis = new Set<string>();
    const obs = new IntersectionObserver(
      (entradas) => {
        for (const e of entradas) {
          if (e.isIntersecting) visiveis.add(e.target.id);
          else visiveis.delete(e.target.id);
        }
        const primeiro = presentes.find((i) => visiveis.has(i.id));
        if (primeiro) setAtivo(primeiro.id);
      },
      { rootMargin: "-120px 0px -60% 0px" },
    );
    for (const i of presentes) {
      const el = document.getElementById(i.id);
      if (el) obs.observe(el);
    }
    return () => obs.disconnect();
  }, [presentes]);

  useEffect(() => {
    const aoRolar = () => setMostrarTopo(window.scrollY > 700);
    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);

  // Mantém a pílula ativa à vista na fileira (só rola a fileira, nunca a página).
  useEffect(() => {
    const lista = fileira.current;
    const el = ativo ? lista?.querySelector<HTMLElement>(`[data-id="${ativo}"]`) : null;
    if (!lista || !el) return;
    lista.scrollTo({ left: el.offsetLeft - lista.clientWidth / 2 + el.clientWidth / 2, behavior: "smooth" });
  }, [ativo]);

  if (presentes.length < 3) return null;

  return (
    <>
      <nav
        aria-label="Seções do perfil"
        className="sticky top-14 z-30 -mx-4 border-b border-border bg-background px-4 lg:top-20 lg:z-auto lg:mx-0 lg:self-start lg:border-b-0 lg:px-0 lg:row-span-2 lg:row-start-1"
      >
        <p className="sobretitulo mb-2 hidden lg:block">Nesta página</p>
        <ul
          ref={fileira}
          className="flex snap-x snap-proximity gap-1 overflow-x-auto lg:flex-col lg:gap-0 lg:overflow-visible"
        >
          {presentes.map((i) => {
            const eAtivo = i.id === ativo;
            return (
              <li key={i.id} data-id={i.id} className="shrink-0 snap-start">
                <a
                  href={`#${i.id}`}
                  aria-current={eAtivo ? "location" : undefined}
                  className={`flex min-h-11 items-center border-b-2 px-3 text-sm whitespace-nowrap lg:border-b-0 lg:border-l-2 lg:px-3 ${
                    eAtivo
                      ? "border-bronze font-semibold text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {i.rotulo}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
      {mostrarTopo && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed right-4 bottom-4 z-30 flex size-11 items-center justify-center rounded-[2px] border border-foreground bg-background text-sm focus-visible:outline-2 focus-visible:outline-bronze"
          aria-label="Voltar ao topo"
        >
          <svg aria-hidden viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      )}
    </>
  );
}
