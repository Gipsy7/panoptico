"use client";

/**
 * Peças do painel privado de acessos: controles, linhas de barra, tabela, gráfico de linha.
 * Só tokens do tema (claro e escuro); nada aqui sabe de onde vêm os números.
 */
import { type ReactNode, useId, useState } from "react";

import { diaCurto, escalaDoEixo } from "@/lib/painel-acessos";

export const num = (n: number) => n.toLocaleString("pt-BR");

const FOCO = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto";

/** Grupo de botões de escolha única (aria-pressed), alvo de toque de 44 px. */
export function Seg<T extends string | number>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
}: {
  rotulo: string;
  opcoes: readonly { v: T; n: string }[];
  valor: T;
  aoMudar: (v: T) => void;
}) {
  return (
    <div role="group" aria-label={rotulo} className="flex flex-wrap gap-1">
      {opcoes.map((o) => (
        <button
          key={String(o.v)}
          type="button"
          aria-pressed={o.v === valor}
          onClick={() => aoMudar(o.v)}
          className={`min-h-11 min-w-11 rounded-sm border border-muted-foreground/60 px-3 text-sm whitespace-nowrap aria-pressed:border-foreground aria-pressed:bg-foreground aria-pressed:font-medium aria-pressed:text-background ${FOCO}`}
        >
          {o.n}
        </button>
      ))}
    </div>
  );
}

/** Linha com nome, valor e uma barra fina. Com `aoClicar`, vira botão (aria-pressed). */
export function Linha({
  nome,
  detalhe,
  valor,
  pct,
  ativo,
  aoClicar,
}: {
  nome: ReactNode;
  detalhe?: string;
  valor: string;
  pct: number;
  ativo?: boolean;
  aoClicar?: () => void;
}) {
  const miolo = (
    <>
      <span className="flex justify-between gap-3 text-sm leading-snug">
        <span className="min-w-0 break-words">
          {nome}
          {detalhe && <span className="block text-xs text-muted-foreground">{detalhe}</span>}
        </span>
        <b className="shrink-0 font-medium tabular-nums">{valor}</b>
      </span>
      <span aria-hidden className="mt-1 block h-1 rounded-sm bg-muted">
        <span className="block h-full rounded-sm bg-bronze" style={{ width: `${Math.max(0.5, Math.min(100, pct))}%` }} />
      </span>
    </>
  );
  const base = "-mx-2 block w-[calc(100%+1rem)] border-b border-border px-2 py-1.5 text-left";
  if (!aoClicar) return <div className={base}>{miolo}</div>;
  return (
    <button
      type="button"
      aria-pressed={!!ativo}
      onClick={aoClicar}
      className={`${base} min-h-11 aria-pressed:bg-accent aria-pressed:shadow-[inset_2px_0_0_var(--foreground)] ${FOCO}`}
    >
      {miolo}
    </button>
  );
}

/** Tabela equivalente ao gráfico ou à lista, dentro de um <details>. */
export function Tabela({
  titulo,
  colunas,
  linhas,
}: {
  titulo: string;
  colunas: string[];
  linhas: (string | number)[][];
}) {
  return (
    <details className="mt-2">
      <summary className={`flex min-h-11 cursor-pointer items-center text-sm text-bronze-texto underline underline-offset-4 ${FOCO}`}>
        Ver como tabela: {titulo.toLowerCase()}
      </summary>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- região rolável precisa de foco para rolar com o teclado */}
      <div role="region" aria-label={titulo} tabIndex={0} className="max-h-80 overflow-auto border-t border-border">
        <table className="w-full text-sm tabular-nums">
          <caption className="py-1.5 text-left text-xs text-muted-foreground">{titulo}</caption>
          <thead>
            <tr>
              {colunas.map((c, i) => (
                <th
                  key={c}
                  scope="col"
                  className={`sticky top-0 bg-background py-1.5 pr-3 text-xs font-normal text-muted-foreground ${i === 0 ? "text-left" : "text-right"}`}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((l, i) => (
              <tr key={i} className="border-t border-border">
                {l.map((c, j) =>
                  j === 0 ? (
                    <th key={j} scope="row" className="py-1.5 pr-3 text-left font-normal">
                      {c}
                    </th>
                  ) : (
                    <td key={j} className="py-1.5 pr-3 text-right whitespace-nowrap">
                      {typeof c === "number" ? num(c) : c}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** Minigráfico de tendência dentro dos números do topo (decorativo; o número vem em texto). */
export function Fagulha({ valores }: { valores: number[] }) {
  const w = 140;
  const h = 26;
  const max = Math.max(1, ...valores);
  const x = (i: number) => (valores.length > 1 ? 2 + (i * (w - 8)) / (valores.length - 1) : w / 2);
  const y = (v: number) => h - 3 - (v / max) * (h - 7);
  const ult = valores.length - 1;
  return (
    <svg aria-hidden viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="my-1 h-6 w-full">
      <path
        d={valores.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join("")}
        fill="none"
        stroke="var(--chart-3)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={x(ult)} cy={y(valores[ult] ?? 0)} r="3" fill="var(--bronze)" />
    </svg>
  );
}

export type SerieDoGrafico = { nome: string; valores: number[]; cor: string };

/**
 * Gráfico de linha de um eixo só, com leitura em texto acima. Funciona com o dedo, o mouse e as
 * setas (role="slider"); a tabela equivalente fica logo abaixo, no mesmo bloco.
 */
export function GraficoDeLinha({
  nome,
  dias,
  series,
  leituraExtra,
}: {
  nome: string;
  dias: { dia: string; semana?: string }[];
  series: SerieDoGrafico[];
  leituraExtra?: (i: number) => ReactNode;
}) {
  const id = useId();
  const [escolhido, setEscolhido] = useState<number | null>(null);
  const n = dias.length;
  const sel = Math.min(escolhido ?? n - 1, n - 1);
  const L = 340;
  const A = 190;
  const mg = { e: 38, d: 10, c: 10, b: 24 };
  const pw = L - mg.e - mg.d;
  const ph = A - mg.c - mg.b;
  const maximo = Math.max(1, ...series.flatMap((s) => s.valores));
  const { topo, passo } = escalaDoEixo(maximo);
  const X = (i: number) => mg.e + (n > 1 ? (i * pw) / (n - 1) : pw / 2);
  const Y = (v: number) => mg.c + ph - (v / topo) * ph;
  const marcas: number[] = [];
  for (let t = 0; t <= topo + 0.001; t += passo) marcas.push(t);
  const rotulosX = [...new Set([0, Math.floor((n - 1) / 2), n - 1])];

  function dePonteiro(e: React.PointerEvent<SVGSVGElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) * L) / r.width;
    setEscolhido(Math.max(0, Math.min(n - 1, n > 1 ? Math.round(((x - mg.e) / pw) * (n - 1)) : 0)));
  }
  function aoTeclar(e: React.KeyboardEvent) {
    const passoTecla = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1 }[e.key];
    if (passoTecla) {
      e.preventDefault();
      setEscolhido(Math.max(0, Math.min(n - 1, sel + passoTecla)));
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      setEscolhido(e.key === "Home" ? 0 : n - 1);
    }
  }
  const d = dias[sel];
  const textoLeitura = `${diaCurto(d.dia)}${d.semana ? `, ${d.semana}` : ""}: ${series.map((s) => `${num(s.valores[sel] ?? 0)} ${s.nome.toLowerCase()}`).join(", ")}`;

  return (
    <div>
      <p id={`${id}-l`} className="flex min-h-12 flex-wrap items-baseline gap-x-3 py-1 text-sm tabular-nums">
        <span>
          {diaCurto(d.dia)}
          {d.semana ? `, ${d.semana}` : ""}
        </span>
        {series.map((s) => (
          <span key={s.nome}>
            <b className="text-xl font-semibold">{num(s.valores[sel] ?? 0)}</b> {s.nome.toLowerCase()}
          </span>
        ))}
        {leituraExtra?.(sel)}
      </p>
      <svg
        role="slider"
        tabIndex={0}
        aria-label={nome}
        aria-valuemin={0}
        aria-valuemax={n - 1}
        aria-valuenow={sel}
        aria-valuetext={textoLeitura}
        aria-orientation="horizontal"
        viewBox={`0 0 ${L} ${A}`}
        className={`h-auto w-full cursor-crosshair touch-pan-y ${FOCO}`}
        onPointerDown={dePonteiro}
        onPointerMove={dePonteiro}
        onKeyDown={aoTeclar}
      >
        {marcas.map((t) => (
          <g key={t}>
            <line x1={mg.e} x2={L - mg.d} y1={Y(t)} y2={Y(t)} stroke="var(--border)" />
            <text x={mg.e - 6} y={Y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted-foreground)">
              {num(t)}
            </text>
          </g>
        ))}
        {rotulosX.map((i) => (
          <text
            key={i}
            x={X(i)}
            y={A - 6}
            fontSize="11"
            fill="var(--muted-foreground)"
            textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}
          >
            {diaCurto(dias[i].dia)}
          </text>
        ))}
        {series.map((s, k) => {
          const caminho = s.valores.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join("");
          return (
            <g key={s.nome}>
              {series.length === 1 && n > 1 && (
                <path d={`${caminho}L${X(n - 1)} ${Y(0)}L${X(0)} ${Y(0)}Z`} fill={s.cor} opacity=".1" />
              )}
              <path d={caminho} fill="none" stroke={s.cor} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={k === 1 ? "5 3" : undefined} />
            </g>
          );
        })}
        <line x1={X(sel)} x2={X(sel)} y1={mg.c} y2={mg.c + ph} stroke="var(--foreground)" />
        {series.map((s) => (
          <circle key={s.nome} cx={X(sel)} cy={Y(s.valores[sel] ?? 0)} r="4" fill={s.cor} stroke="var(--background)" strokeWidth="2" />
        ))}
      </svg>
      {series.length > 1 && (
        <p className="flex flex-wrap gap-x-4 text-xs text-muted-foreground">
          {series.map((s, k) => (
            <span key={s.nome} className="inline-flex items-center gap-1.5">
              <svg aria-hidden width="18" height="4">
                <line x1="0" x2="18" y1="2" y2="2" stroke={s.cor} strokeWidth="2" strokeDasharray={k === 1 ? "5 3" : undefined} />
              </svg>
              {s.nome}
            </span>
          ))}
        </p>
      )}
    </div>
  );
}

export function Bloco({
  id,
  titulo,
  children,
  nota,
}: {
  id: string;
  titulo: string;
  children: ReactNode;
  nota?: string;
}) {
  return (
    <section aria-labelledby={id} className="min-w-0">
      <h2 id={id} className="text-base font-semibold">
        {titulo}
      </h2>
      {nota && <p className="text-xs text-muted-foreground">{nota}</p>}
      <div className="mt-1">{children}</div>
    </section>
  );
}

export function Vazio({ children }: { children: ReactNode }) {
  return <p className="py-2 text-sm text-muted-foreground">{children}</p>;
}
