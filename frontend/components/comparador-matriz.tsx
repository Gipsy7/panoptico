"use client";

import { useState } from "react";

import { formatarData } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

export type DivergenciaPar = {
  data: string | null;
  titulo: string | null;
  ementa: string | null;
  descricao: string | null;
  resultado: string | null;
  url: string | null;
  /** Voto de quem tem o menor índice no par (i). */
  voto_i: string;
  voto_j: string;
};

export type ParMatriz = {
  i: number;
  j: number;
  mesmaCasa: boolean;
  total: number;
  iguais: number;
  porTema: { tema: string; iguais: number; total: number }[];
  divergencias: DivergenciaPar[];
};

const PCT = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%`;

/**
 * Votos em comum, par a par. Cada célula mostra o percentual e "X de Y"; tocar nela abre as
 * divergências recentes e a quebra por tema. A cor só varia entre o cinza e o bronze.
 */
export function ComparadorMatriz({
  nomes,
  pares,
  periodo,
}: {
  nomes: string[];
  pares: ParMatriz[];
  /** Texto do recorte, ex.: "votações nominais do Plenário em 2026". */
  periodo: string;
}) {
  const busca = (i: number, j: number) => pares.find((p) => p.i === Math.min(i, j) && p.j === Math.max(i, j));
  const inicial = nomes.length === 2 ? pares.find((p) => p.mesmaCasa && p.total > 0) : undefined;
  const [aberto, setAberto] = useState<[number, number] | null>(inicial ? [inicial.i, inicial.j] : null);
  const par = aberto ? busca(aberto[0], aberto[1]) : undefined;

  return (
    <div className="flex flex-col gap-4">
      <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
        <table
          style={{ minWidth: 96 + nomes.length * 80 }}
          className="w-full table-fixed border-separate border-spacing-0 text-sm"
        >
          <caption className="sr-only">
            Votações em que cada par votou igual, em {periodo}. Escolha uma célula para ver os detalhes.
          </caption>
          <thead>
            <tr>
              <td className="sticky left-0 z-10 w-24 bg-background md:w-40" />
              {nomes.map((n, j) => (
                <th key={j} scope="col" className="px-1 pb-2 text-left align-bottom font-semibold leading-tight">
                  <span className="line-clamp-2 break-words text-sm" title={n}>
                    {n}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {nomes.map((n, i) => (
              <tr key={i}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 border-t border-border bg-background py-1 pr-2 text-left font-semibold leading-tight"
                >
                  <span className="line-clamp-2 break-words text-sm" title={n}>
                    {n}
                  </span>
                </th>
                {nomes.map((_, j) => (
                  <td key={j} className="border-t border-border p-1 align-top">
                    {i === j ? (
                      <span aria-hidden className="flex h-14 items-center justify-center text-muted-foreground">
                        —
                      </span>
                    ) : (
                      <Celula
                        nomeI={n}
                        nomeJ={nomes[j]}
                        par={busca(i, j)}
                        ativa={!!aberto && Math.min(i, j) === aberto[0] && Math.max(i, j) === aberto[1]}
                        abrir={() => setAberto([Math.min(i, j), Math.max(i, j)])}
                      />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div aria-live="polite">
        {par ? (
          <Detalhe par={par} nomeI={nomes[par.i]} nomeJ={nomes[par.j]} periodo={periodo} />
        ) : (
          <p className="text-sm text-muted-foreground">
            Toque ou clique numa célula para ver em quais votações o par votou diferente.
          </p>
        )}
      </div>
    </div>
  );
}

function Celula({
  nomeI,
  nomeJ,
  par,
  ativa,
  abrir,
}: {
  nomeI: string;
  nomeJ: string;
  par: ParMatriz | undefined;
  ativa: boolean;
  abrir: () => void;
}) {
  if (!par || !par.mesmaCasa) {
    return (
      <span className="flex h-14 items-center justify-center px-1 text-center text-sm leading-tight text-muted-foreground">
        Casas diferentes
      </span>
    );
  }
  if (par.total === 0) {
    return (
      <span className="flex h-14 items-center justify-center px-1 text-center text-sm leading-tight text-muted-foreground">
        Sem votos em comum
      </span>
    );
  }
  const pct = (100 * par.iguais) / par.total;
  // Opacidade do bronze de 20% a 60%, sobre o cinza do trilho.
  const bronze = 20 + 40 * (pct / 100);
  return (
    <button
      type="button"
      onClick={abrir}
      aria-pressed={ativa}
      aria-label={`${nomeI} e ${nomeJ}: votaram igual em ${par.iguais} de ${par.total} votações, ${PCT(pct)}. Ver detalhes`}
      style={{ background: `color-mix(in oklab, var(--bronze) ${bronze}%, var(--muted))` }}
      className={`flex h-14 min-h-11 w-full flex-col items-center justify-center rounded-[2px] border leading-tight tabular-nums focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze ${
        ativa ? "border-foreground" : "border-transparent"
      }`}
    >
      <span className="text-sm font-semibold">{PCT(pct)}</span>
      <span className="text-sm">
        {par.iguais} de {par.total}
      </span>
    </button>
  );
}

function Detalhe({ par, nomeI, nomeJ, periodo }: { par: ParMatriz; nomeI: string; nomeJ: string; periodo: string }) {
  if (!par.mesmaCasa) {
    return (
      <p className="nota text-sm text-muted-foreground">
        {nomeI} e {nomeJ} são de Casas diferentes, que votam em votações diferentes. Não dá para comparar os votos.
      </p>
    );
  }
  if (par.total === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {nomeI} e {nomeJ} não votaram nas mesmas votações nominais em {periodo}.
      </p>
    );
  }
  const pct = (100 * par.iguais) / par.total;
  return (
    <div className="flex flex-col gap-3">
      <div className="figura">
        <p className="text-sm text-muted-foreground">
          {nomeI} e {nomeJ} votaram igual em
        </p>
        <p className="numero text-3xl">
          {par.iguais} de {par.total} votações
        </p>
        <p className="text-sm text-muted-foreground tabular-nums">
          {pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% das votações em que os dois
          votaram ({periodo})
        </p>
      </div>
      {par.porTema.length > 0 && (
        <details className="painel">
          <summary className="flex min-h-11 cursor-pointer items-center font-medium">Votos iguais por tema</summary>
          <ul className="lista-fios mt-2 flex flex-col">
            {par.porTema.map((t) => (
              <li key={t.tema} className="flex min-h-11 items-center justify-between gap-3 py-2 text-sm">
                <span>{t.tema}</span>
                <span className="tabular-nums">
                  {t.iguais} de {t.total}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {par.divergencias.length > 0 && (
        <details className="painel">
          <summary className="flex min-h-11 cursor-pointer items-center font-medium">
            Onde votaram diferente (mais recentes)
          </summary>
          <ul className="lista-fios mt-2 flex flex-col">
            {par.divergencias.map((d, k) => (
              <li key={k} className="flex flex-col gap-1 py-3">
                <span className="text-sm text-muted-foreground">
                  {[d.data && formatarData(d.data), d.resultado].filter(Boolean).join(" · ")}
                </span>
                {d.titulo &&
                  (d.url ? (
                    <LinkExterno href={d.url} className="font-medium underline underline-offset-2">
                      {d.titulo}
                    </LinkExterno>
                  ) : (
                    <span className="font-medium">{d.titulo}</span>
                  ))}
                {d.ementa && <p className="line-clamp-3 text-sm">{d.ementa}</p>}
                {d.descricao && <p className="line-clamp-2 text-sm text-muted-foreground">{d.descricao}</p>}
                <dl className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-sm text-muted-foreground">{nomeI}</dt>
                    <dd className="font-semibold">{d.voto_i}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">{nomeJ}</dt>
                    <dd className="font-semibold">{d.voto_j}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
