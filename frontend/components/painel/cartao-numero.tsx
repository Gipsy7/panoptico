/**
 * Cartão do topo do painel: rótulo do dia a dia, número grande em serifa e a comparação
 * (barras pessoa x média na mesma escala, ou uma linha "Média X"). O cartão inteiro é um
 * link para `#ver-<destino>`; o <AbasDetalhe> da mesma página abre a seção com esse id numa
 * gaveta. Sem JS, o link só leva até a seção.
 *
 * Uso (servidor):
 *   <GradeCartoes rotulo="Números principais">
 *     <CartaoNumero destino="presenca" rotulo="Votou em 2026" valor="7 de 123" largo
 *       comparacao={{ pessoa: { rotulo: "Arthur Lira", valor: 5.7 },
 *                     media: { rotulo: "Média da Câmara", valor: 78.8 },
 *                     formato: "percentual", escala: 100 }} />
 *     <CartaoNumero destino="gastos" rotulo="Verba do gabinete" valor="R$ 74 mil" apoio="Média R$ 252 mil" />
 *   </GradeCartoes>
 * `destino` precisa existir como seção em <AbasDetalhe> (id "ver-<destino>").
 */
import type { ReactNode } from "react";

import { BarraComparacao, type FormatoNumero } from "@/components/painel/barra-comparacao";

export type Comparacao = {
  pessoa: { rotulo: string; valor: number };
  media: { rotulo: string; valor: number };
  formato: FormatoNumero;
  escala?: number;
};

export function GradeCartoes({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <ul aria-label={rotulo} className="grid grid-cols-2 gap-2 sm:gap-3 lg:grid-cols-4">
      {children}
    </ul>
  );
}

export function CartaoNumero({
  destino,
  rotulo,
  valor,
  complemento,
  comparacao,
  apoio,
  largo,
  href,
}: {
  destino: string;
  rotulo: string;
  /** O número grande. */
  valor: string;
  /** Texto menor logo após o número (ex.: "de 123"). */
  complemento?: string;
  comparacao?: Comparacao;
  /** Linha de apoio quando não há barra (ex.: "Média R$ 252 mil", "Igual para todos"). */
  apoio?: string;
  /** Ocupa as duas colunas no celular. */
  largo?: boolean;
  /** Link para outra página (em vez de abrir a gaveta `#ver-<destino>`); `destino` fica ignorado. */
  href?: string;
}) {
  return (
    <li className={`min-w-0 ${largo ? "col-span-2" : ""}`}>
      <a
        href={href ?? `#ver-${destino}`}
        className="flex h-full min-h-11 min-w-0 flex-col gap-2 rounded-[var(--radius)] border border-border bg-card p-3 transition-colors duration-200 hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze sm:p-4"
      >
        <span className="text-sm leading-snug text-muted-foreground">{rotulo}</span>
        <span className="numero text-[1.375rem] leading-none break-words sm:text-[1.625rem]">
          {valor}
          {complemento && <span className="text-base text-muted-foreground"> {complemento}</span>}
        </span>
        {comparacao && <BarraComparacao {...comparacao} />}
        {apoio && <span className="text-sm text-muted-foreground tabular-nums">{apoio}</span>}
        <span className="mt-auto pt-1 text-sm text-bronze-texto" aria-hidden>
          Ver detalhe ›
        </span>
      </a>
    </li>
  );
}
