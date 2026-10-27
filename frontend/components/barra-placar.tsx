/**
 * Barra de placar Sim x Não: Sim em bronze, Não em cinza (tokens do tema), como no explicador de
 * votação. Sem cor de aprovado/rejeitado; o número vem sempre escrito ao lado.
 */
const INTEIRO = new Intl.NumberFormat("pt-BR");

export function BarraPlacar({ sim, nao, className = "" }: { sim: number; nao: number; className?: string }) {
  if (sim + nao <= 0) return null;
  return (
    <div
      aria-hidden
      className={`flex h-2 w-full gap-px overflow-hidden rounded-[2px] bg-muted ${className}`}
    >
      <span className="h-full bg-bronze" style={{ flexGrow: sim }} />
      <span className="h-full bg-chart-3" style={{ flexGrow: nao }} />
    </div>
  );
}

/** "300 Sim × 100 Não", com a barra embaixo. */
export function PlacarCompacto({ sim, nao }: { sim: number; nao: number }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="numero text-xl leading-none tabular-nums">
        {INTEIRO.format(sim)} <span className="text-sm text-muted-foreground">Sim</span> × {INTEIRO.format(nao)}{" "}
        <span className="text-sm text-muted-foreground">Não</span>
      </p>
      <BarraPlacar sim={sim} nao={nao} />
    </div>
  );
}

/** Cartão largo do topo da página de projeto, com o último placar. Aponta para `#ver-<destino>`. */
export function CartaoPlacarLink({
  destino,
  rotulo,
  sim,
  nao,
  apoio,
}: {
  destino: string;
  rotulo: string;
  sim: number;
  nao: number;
  apoio: string;
}) {
  return (
    <li className="col-span-2 min-w-0">
      <a
        href={`#ver-${destino}`}
        className="flex h-full min-h-11 min-w-0 flex-col gap-2 rounded-[var(--radius)] border border-border bg-card p-3 transition-colors duration-200 hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze sm:p-4"
      >
        <span className="text-sm leading-snug text-muted-foreground">{rotulo}</span>
        <span className="numero text-[1.375rem] leading-none sm:text-[1.625rem]">
          {INTEIRO.format(sim)} <span className="text-base text-muted-foreground">Sim</span> × {INTEIRO.format(nao)}{" "}
          <span className="text-base text-muted-foreground">Não</span>
        </span>
        <BarraPlacar sim={sim} nao={nao} />
        <span className="text-sm text-muted-foreground tabular-nums">{apoio}</span>
        <span className="mt-auto pt-1 text-sm text-bronze-texto" aria-hidden>
          Ver detalhe ›
        </span>
      </a>
    </li>
  );
}
