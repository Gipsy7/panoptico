"use client";

// Peças de apresentação do painel: seção recolhida, figura com apoio, barras de decomposição.

import { type ReactNode, useState } from "react";

export function Secao({
  titulo,
  children,
  aberta,
  preguicosa,
}: {
  titulo: string;
  children: ReactNode;
  aberta?: boolean;
  /** Só monta o conteúdo depois da primeira abertura (para buscar dados sob demanda). */
  preguicosa?: boolean;
}) {
  const [viu, setViu] = useState(Boolean(aberta));
  return (
    <details
      className="group border-t border-border"
      open={aberta}
      onToggle={(e) => e.currentTarget.open && setViu(true)}
    >
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 text-[15px] font-medium [&::-webkit-details-marker]:hidden">
        {titulo}
        <span
          aria-hidden
          className="mr-1 mb-1 size-2 shrink-0 rotate-45 border-r-[1.5px] border-b-[1.5px] border-muted-foreground transition-transform group-open:mt-1 group-open:mb-0 group-open:-rotate-[135deg]"
        />
      </summary>
      <div className="flex flex-col gap-3 pb-4">{!preguicosa || viu ? children : null}</div>
    </details>
  );
}

export function Figura({ rotulo, valor, apoio }: { rotulo: string; valor: string; apoio?: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 border-t border-foreground pt-2">
      <span className="text-[13px] text-muted-foreground">{rotulo}</span>
      <span className="font-heading text-[1.65rem] leading-tight tabular-nums">{valor}</span>
      {apoio && <span className="text-[13px] text-muted-foreground">{apoio}</span>}
    </div>
  );
}

export type ItemBarra = { nome: string; oficial?: string; valor: number | null; destaque?: boolean; extra?: string };

/** Lista de barras na mesma escala; o valor sempre escrito ao lado. */
export function Barras({ itens, rotulo }: { itens: ItemBarra[]; rotulo: string }) {
  const max = Math.max(...itens.map((i) => i.valor ?? 0), 1);
  return (
    <ul aria-label={rotulo} className="flex flex-col gap-2.5">
      {itens.map((i) => (
        <li key={i.nome} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className={i.destaque ? "font-medium" : undefined}>
              {i.nome}
              {i.oficial && <span className="block text-[13px] text-muted-foreground">{i.oficial}</span>}
            </span>
            <span className="shrink-0 tabular-nums">{i.extra ?? ""}</span>
          </div>
          <div aria-hidden className="h-1.5 w-full bg-muted">
            <div
              className={`h-full ${i.destaque ? "bg-foreground" : "bg-bronze"}`}
              style={{ width: `${i.valor == null ? 0 : Math.max(1, (i.valor / max) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
