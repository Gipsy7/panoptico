"use client";

// Lista no lugar do mapa: estados (no Brasil) ou cidades (dentro de um estado), com colunas ordenáveis.

import { useMemo, useState } from "react";

import { numero, porHab, reais, reaisA100 } from "./formatos";

export type LinhaLista = { id: string; nome: string; c1: number | null; c2: number | null; c3: number | null; c4: number | null };

export function ListaLugares({
  linhas,
  nivel,
  legenda,
  onEscolher,
}: {
  linhas: LinhaLista[];
  nivel: "uf" | "mun";
  legenda: string;
  onEscolher: (id: string) => void;
}) {
  const [ordem, setOrdem] = useState<{ k: keyof LinhaLista; dir: 1 | -1 }>({ k: "nome", dir: 1 });
  const cab: [keyof LinhaLista, string][] =
    nivel === "uf"
      ? [["nome", "Estado"], ["c1", "A União arrecadou"], ["c2", "Repassou"], ["c3", "Repasse por habitante"], ["c4", "Repasse a cada R$ 100"]]
      : [["nome", "Cidade"], ["c1", "Moradores"], ["c2", "Repasse à prefeitura"], ["c3", "Repasse por morador"]];
  const fmt =
    nivel === "uf" ? [reais, reais, porHab, reaisA100] : [numero, reais, porHab];
  const ordenadas = useMemo(() => {
    const l = [...linhas];
    l.sort((a, b) => {
      if (ordem.k === "nome") return a.nome.localeCompare(b.nome, "pt-BR") * ordem.dir;
      const va = a[ordem.k] as number | null;
      const vb = b[ordem.k] as number | null;
      if (va == null) return 1;
      if (vb == null) return -1;
      return (va - vb) * ordem.dir;
    });
    return l;
  }, [linhas, ordem]);
  const colunas = cab.length;

  return (
    <div className="min-h-0 flex-1 overflow-auto p-3 lg:max-h-[min(72vh,640px)] lg:p-4">
      <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
        <caption className="pb-2 text-left text-sm text-muted-foreground">
          {legenda} Toque ou clique no título da coluna para ordenar.
        </caption>
        <thead>
          <tr>
            {cab.map(([k, t], i) => (
              <th
                key={k}
                scope="col"
                aria-sort={ordem.k === k ? (ordem.dir > 0 ? "ascending" : "descending") : "none"}
                className={`border-b border-border bg-card p-0 font-medium ${i === 0 ? "sticky left-0 z-10" : "text-right"}`}
              >
                <button
                  type="button"
                  onClick={() =>
                    setOrdem((o) => ({ k, dir: o.k === k ? (o.dir === 1 ? -1 : 1) : k === "nome" ? 1 : -1 }))
                  }
                  className={`min-h-11 w-full px-2 ${i === 0 ? "text-left" : "text-right"}`}
                >
                  {t}
                  {ordem.k === k ? (ordem.dir > 0 ? " ↑" : " ↓") : ""}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordenadas.map((l) => (
            <tr key={l.id} className="border-b border-border/60">
              <th scope="row" className="sticky left-0 bg-card p-0 text-left font-normal">
                <button type="button" onClick={() => onEscolher(l.id)} className="min-h-11 w-full px-2 text-left underline-offset-4 hover:underline">
                  {l.nome}
                </button>
              </th>
              {Array.from({ length: colunas - 1 }, (_, i) => (
                <td key={i} className="px-2 text-right tabular-nums">
                  {fmt[i](l[`c${i + 1}` as "c1" | "c2" | "c3" | "c4"])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
