import { cn } from "@/lib/utils";

/**
 * Esqueleto de carregamento que mostra a estrutura da seção (sobretítulo, título e linhas de
 * texto) em vez de um bloco cinza. A animação some com "reduzir movimento" (ver globals.css).
 */
export function EsqueletoSecao({
  rotulo = "Carregando…",
  secoes = 1,
  linhas = 3,
  className,
}: {
  rotulo?: string;
  secoes?: number;
  linhas?: number;
  className?: string;
}) {
  const barra = "animate-pulse motion-reduce:animate-none rounded-[2px] bg-muted";
  return (
    <div className={cn("flex flex-col gap-[var(--esp-10)]", className)}>
      <span role="status" className="sr-only">
        {rotulo}
      </span>
      {Array.from({ length: secoes }, (_, s) => (
        <div key={s} aria-hidden className="flex flex-col gap-[var(--esp-3)]">
          <div className={cn(barra, "h-3 w-24")} />
          <div className={cn(barra, "h-7 w-2/3")} />
          <div className="flex flex-col gap-[var(--esp-2)]">
            {Array.from({ length: linhas }, (_, i) => (
              <div key={i} className={cn(barra, "h-5", i === linhas - 1 ? "w-1/2" : "w-full")} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
