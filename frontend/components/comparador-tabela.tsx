import Link from "next/link";
import type { ReactNode } from "react";

import { ComparadorQuadro } from "@/components/comparador-quadro";

export type ColunaPessoa = {
  id: string | number;
  nome: string;
  /** Partido e UF, ou só o partido. */
  sub: string;
  /** Perfil da pessoa. */
  href: string;
  foto: ReactNode;
  /** Endereço da comparação sem esta pessoa. */
  remover: string;
};

export type CelulaTabela = {
  texto: string;
  /** Barra neutra: `escala` é o valor que enche o trilho; `media` é a marca da Casa. */
  barra?: { valor: number | null; escala: number; media: number | null };
  /** Linha pequena abaixo (ex.: "média Câmara R$ 250 mil"). */
  media?: string;
};

export type LinhaTabela = { id: string; rotulo: string; detalhe?: string; celulas: CelulaTabela[] };

export type GrupoTabela = { id: string; titulo: string; linhas: LinhaTabela[]; nota?: ReactNode };

const MAXIMO = 4;

/**
 * Tabela de 2 a 4 pessoas: coluna de rótulos fixa, cabeçalho fixo com foto e nome, linhas de
 * altura única e rolagem lateral com encaixe no celular. É uma `<table>` de verdade: o leitor de
 * tela anuncia a linha ("Gastos") e a pessoa de cada valor.
 */
export function ComparadorTabela({
  colunas,
  grupos,
  adicionar,
  legenda,
  mensagemVazia = "Nenhuma diferença neste grupo.",
}: {
  colunas: ColunaPessoa[];
  grupos: GrupoTabela[];
  /** Endereço que abre a busca para acrescentar alguém; nulo quando já são 4. */
  adicionar: string | null;
  legenda: string;
  mensagemVazia?: string;
}) {
  const comAdicionar = adicionar !== null && colunas.length < MAXIMO;
  const total = colunas.length + (comAdicionar ? 1 : 0);

  const cabecalho = (
    <>
      <div className="sticky left-0 z-20 flex items-end bg-background pb-2 pl-4 md:pl-0">
        <span className="sobretitulo hidden md:inline">{legenda}</span>
      </div>
      {colunas.map((c) => (
        <div key={c.id} className="flex snap-start flex-col gap-2 px-2 pb-2 pt-2">
          <Link href={c.href} className="flex flex-col gap-1 hover:opacity-80">
            {c.foto}
            <span className="line-clamp-2 min-h-[2.5em] break-words text-sm font-semibold leading-tight">
              {c.nome}
            </span>
            <span className="text-[13px] leading-tight text-muted-foreground">{c.sub}</span>
          </Link>
          <Link href={c.remover} className="botao-linha mt-auto w-full px-2!">
            Remover<span className="sr-only"> {c.nome}</span>
          </Link>
        </div>
      ))}
      {comAdicionar && (
        <div className="flex snap-start flex-col justify-end px-2 pb-2 pt-2">
          <Link href={adicionar} className="botao-linha w-full px-2!">
            + Adicionar
          </Link>
        </div>
      )}
    </>
  );

  return (
    <ComparadorQuadro cabecalho={cabecalho} colunas={total}>
      <table
        className="w-full min-w-[calc(132px_+_var(--c)*104px)] table-fixed border-separate border-spacing-0 text-left text-sm md:min-w-0"
      >
        <caption className="sr-only">{legenda}. Cada linha traz o valor de cada pessoa.</caption>
        <colgroup>
          <col className="w-[132px] md:w-[200px]" />
          {Array.from({ length: total }, (_, i) => (
            <col key={i} className="w-[104px] md:w-auto" />
          ))}
        </colgroup>
        <thead className="sr-only">
          <tr>
            <th scope="col">Item</th>
            {colunas.map((c) => (
              <th key={c.id} scope="col">
                {c.nome}, {c.sub}
              </th>
            ))}
            {comAdicionar && (
              <th scope="col">
                <span className="sr-only">Espaço para adicionar outra pessoa</span>
              </th>
            )}
          </tr>
        </thead>
        {grupos.map((g) => (
          <tbody key={g.id}>
            <tr>
              <th
                colSpan={total + 1}
                scope="colgroup"
                className="h-11 border-b border-border p-0 text-left align-bottom font-normal"
              >
                <span className="sticky left-0 inline-block pb-1 pl-4 md:pl-0">
                  <span className="sobretitulo">{g.titulo}</span>
                </span>
              </th>
            </tr>
            {g.linhas.length === 0 ? (
              <tr>
                <td colSpan={total + 1} className="border-b border-border p-0 text-muted-foreground">
                  <span className="sticky left-0 inline-block py-3 pl-4 md:pl-0">{mensagemVazia}</span>
                </td>
              </tr>
            ) : (
              g.linhas.map((l) => (
                <tr key={l.id} className="h-20">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-b border-r border-border bg-background py-2 pl-4 pr-2 text-left align-top font-normal md:pl-0"
                  >
                    <span className="block [overflow-wrap:normal] text-sm leading-tight">{l.rotulo}</span>
                    {l.detalhe && (
                      <span className="mt-1 block text-[13px] leading-tight text-muted-foreground">{l.detalhe}</span>
                    )}
                  </th>
                  {l.celulas.map((c, i) => (
                    <td key={colunas[i]?.id ?? i} className="snap-start border-b border-border px-2 py-2 align-top">
                      <Celula c={c} />
                    </td>
                  ))}
                  {comAdicionar && <td className="snap-start border-b border-border" />}
                </tr>
              ))
            )}
          </tbody>
        ))}
      </table>
    </ComparadorQuadro>
  );
}

function Celula({ c }: { c: CelulaTabela }) {
  const b = c.barra;
  const pct = (v: number | null) =>
    v !== null && b && b.escala > 0 ? Math.min(100, Math.max(0, (v / b.escala) * 100)) : null;
  const largura = b ? pct(b.valor) : null;
  const marca = b ? pct(b.media) : null;
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="break-words font-medium tabular-nums leading-tight">{c.texto}</span>
      {b && largura !== null && (
        <span aria-hidden className="relative block h-2 w-full rounded-[2px] bg-muted">
          <span
            className="block h-2 rounded-[2px] bg-bronze"
            style={{ width: `${largura === 0 ? 0 : Math.max(2, largura)}%` }}
          />
          {marca !== null && (
            <span className="absolute -top-0.5 block h-3 w-0.5 bg-foreground" style={{ left: `calc(${marca}% - 1px)` }} />
          )}
        </span>
      )}
      {c.media && <span className="text-[13px] leading-tight text-muted-foreground">{c.media}</span>}
    </div>
  );
}
