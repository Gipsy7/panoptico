"use client";

import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Texto longo (ementa, biografia) cortado em poucas linhas, com botão "Ver mais" de 44 px.
 * O botão só aparece quando o texto de fato passa do corte; sem JavaScript, o corte continua
 * e o texto inteiro fica no HTML (leitores de tela e busca leem tudo).
 */
export function TextoLongo({
  children,
  linhas = 3,
  className,
}: {
  children: string;
  linhas?: 2 | 3 | 4 | 5;
  className?: string;
}) {
  const ref = useRef<HTMLParagraphElement>(null);
  const id = useId();
  const [aberto, setAberto] = useState(false);
  const [corta, setCorta] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const medir = () => {
      if (!aberto) setCorta(el.scrollHeight > el.clientHeight + 1);
    };
    medir();
    const obs = new ResizeObserver(medir);
    obs.observe(el);
    return () => obs.disconnect();
  }, [aberto, children]);

  const corte = { 2: "line-clamp-2", 3: "line-clamp-3", 4: "line-clamp-4", 5: "line-clamp-5" }[linhas];

  return (
    <div className="flex flex-col items-start">
      <p id={id} ref={ref} className={cn("text-sm break-words", !aberto && corte, className)}>
        {children}
      </p>
      {(corta || aberto) && (
        <button
          type="button"
          aria-expanded={aberto}
          aria-controls={id}
          onClick={() => setAberto((v) => !v)}
          className="alvo-link text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
        >
          {aberto ? "Ver menos" : "Ver mais"}
        </button>
      )}
    </div>
  );
}
