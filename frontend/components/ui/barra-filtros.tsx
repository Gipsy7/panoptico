import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * Barra de filtros das listas: contador do que está ativo, painel opcional com o formulário
 * completo e uma fileira de pílulas que rola na horizontal. Todo o estado vive na URL: cada
 * pílula é um link, então não há JavaScript no cliente e o endereço é compartilhável.
 */
export type Pilula = {
  rotulo: string;
  href: string;
  ativa?: boolean;
  /** Pílula de filtro ativo com "×": o link tira esse filtro. */
  remover?: boolean;
};

export type GrupoPilulas = { titulo?: string; itens: Pilula[] };

export function BarraFiltros({
  contador,
  grupos,
  limparHref,
  painel,
  rotulo = "Filtros",
}: {
  contador: number;
  grupos: GrupoPilulas[];
  limparHref?: string;
  painel?: React.ReactNode;
  rotulo?: string;
}) {
  const textoContador = contador > 0 ? `${rotulo} (${contador})` : rotulo;
  const descricao =
    contador === 0 ? "nenhum filtro ativo" : contador === 1 ? "1 filtro ativo" : `${contador} filtros ativos`;
  const limpar =
    contador > 0 && limparHref ? (
      <Link href={limparHref} className="alvo-link text-sm underline underline-offset-4">
        Limpar
      </Link>
    ) : null;

  return (
    <div className="flex flex-col gap-[var(--esp-3)]">
      {painel ? (
        <details className="group">
          <summary
            className={cn(
              "flex min-h-11 cursor-pointer list-none items-center gap-[var(--esp-2)] text-sm font-medium",
              "[&::-webkit-details-marker]:hidden",
            )}
          >
            <span className="inline-flex min-h-11 items-center border border-border px-[var(--esp-4)] group-open:border-foreground">
              {textoContador}
              <span className="sr-only">: {descricao}</span>
              <span aria-hidden className="ml-[var(--esp-2)] text-muted-foreground group-open:hidden">
                +
              </span>
              <span aria-hidden className="ml-[var(--esp-2)] hidden text-muted-foreground group-open:inline">
                −
              </span>
            </span>
          </summary>
          <div className="painel mt-[var(--esp-2)]">{painel}</div>
        </details>
      ) : (
        <p className="flex min-h-11 items-center text-sm">
          <span className="font-medium">
            {textoContador}
            <span className="sr-only">: {descricao}</span>
          </span>
        </p>
      )}

      <div
        role="group"
        aria-label="Atalhos de filtro"
        className="-mx-4 flex snap-x snap-proximity items-center gap-[var(--esp-2)] overflow-x-auto px-4 pb-[var(--esp-1)]"
      >
        {grupos.map((grupo, g) => (
          <div key={g} className="flex shrink-0 items-center gap-[var(--esp-2)]">
            {g > 0 && <span aria-hidden className="mx-[var(--esp-1)] h-6 w-px bg-border" />}
            {grupo.titulo && <span className="shrink-0 text-sm text-muted-foreground">{grupo.titulo}</span>}
            {grupo.itens.map((p) => (
              <Link
                key={`${p.rotulo}-${p.href}`}
                href={p.href}
                scroll={false}
                aria-current={p.ativa ? "true" : undefined}
                aria-label={p.remover ? `Tirar filtro ${p.rotulo}` : undefined}
                className={cn(
                  "inline-flex min-h-11 shrink-0 snap-start items-center border px-[var(--esp-3)] text-sm whitespace-nowrap transition-colors",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze",
                  p.ativa || p.remover
                    ? "border-foreground bg-accent font-semibold"
                    : "border-border hover:bg-accent/50",
                )}
              >
                {p.rotulo}
                {p.remover && (
                  <span aria-hidden className="ml-[var(--esp-2)]">
                    ×
                  </span>
                )}
              </Link>
            ))}
          </div>
        ))}
        {limpar && <div className="shrink-0 pl-[var(--esp-2)]">{limpar}</div>}
      </div>
    </div>
  );
}
