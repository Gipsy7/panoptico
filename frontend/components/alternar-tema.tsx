"use client";

import { useSyncExternalStore } from "react";

type Tema = "system" | "light" | "dark";

const OPCOES: { valor: Tema; rotulo: string }[] = [
  { valor: "system", rotulo: "Automático" },
  { valor: "light", rotulo: "Claro" },
  { valor: "dark", rotulo: "Escuro" },
];

function aplicar(tema: Tema) {
  const raiz = document.documentElement;
  if (tema === "system") raiz.removeAttribute("data-theme");
  else raiz.setAttribute("data-theme", tema);
}

/**
 * Escolha do tema: automático (segue o sistema), claro ou escuro. A preferência fica no
 * localStorage (chave "tema"); o script do <head> em layout.tsx a aplica antes da pintura.
 */
function observar(aviso: () => void) {
  const o = new MutationObserver(aviso);
  o.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => o.disconnect();
}

function atual(): Tema {
  const t = document.documentElement.getAttribute("data-theme");
  return t === "light" || t === "dark" ? t : "system";
}

export function AlternarTema({ className = "" }: { className?: string }) {
  // O tema vive no atributo data-theme da página (aplicado pelo script do <head>).
  const tema = useSyncExternalStore(observar, atual, () => "system" as Tema);

  function escolher(novo: Tema) {
    aplicar(novo);
    try {
      if (novo === "system") localStorage.removeItem("tema");
      else localStorage.setItem("tema", novo);
    } catch {}
  }

  return (
    <div role="group" aria-label="Tema do site" className={`flex items-center gap-1 text-sm ${className}`}>
      {OPCOES.map((o) => (
        <button
          key={o.valor}
          type="button"
          aria-pressed={tema === o.valor}
          onClick={() => escolher(o.valor)}
          className={`alvo-44 rounded-[2px] px-2 focus-visible:outline-2 focus-visible:outline-bronze ${
            tema === o.valor ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {o.rotulo}
        </button>
      ))}
    </div>
  );
}
