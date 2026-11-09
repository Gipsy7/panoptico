import Link from "next/link";

import { type Assunto, IconeAssunto } from "@/components/icone-assunto";

/**
 * "Ligado a" (navegação por relacionamento): chips com ícone que levam do assunto atual a outros
 * ligados a ele (partido, lugar, pessoas, Mapa, projetos), o mesmo desenho em perfis, partidos,
 * projetos e no Mapa. Tracejado = "dá para ir até lá"; a seta reforça.
 */
export type Ligacao = { icone: Assunto; rotulo: string; href: string };

export function LigadoA({ itens, titulo = "Ligado a" }: { itens: Ligacao[]; titulo?: string }) {
  if (itens.length === 0) return null;
  return (
    <nav aria-label={titulo} className="flex flex-col gap-1.5">
      <p className="text-xs text-muted-foreground">{titulo}</p>
      <ul className="flex flex-wrap gap-1.5">
        {itens.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="group inline-flex min-h-9 items-center gap-1.5 rounded-full border border-dashed border-muted-foreground bg-background py-1 pr-3 pl-2 text-sm hover:border-solid hover:border-foreground"
            >
              <span className="text-bronze">
                <IconeAssunto assunto={l.icone} className="size-4" />
              </span>
              {l.rotulo}
              <span aria-hidden className="transition-transform group-hover:translate-x-0.5">
                →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
