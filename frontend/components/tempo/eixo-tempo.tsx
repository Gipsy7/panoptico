"use client";

/**
 * Peças da linha do tempo (protótipos B e C): faixas de gestão, uma linha por série, o eixo de
 * anos e o painel do ano, todos no mesmo domínio de anos.
 *
 * Interação: passar o dedo ou o mouse sobre qualquer gráfico marca o ano em todos (linha vertical)
 * e o painel do ano diz quem governava e o valor de cada série; no teclado, as setas mudam o ano.
 * Os textos são HTML posicionado em %, e o SVG só desenha as linhas (sem distorcer letra), para caber
 * em 320 px sem rolagem lateral.
 */
import { type KeyboardEvent, type PointerEvent, useState } from "react";

import type { Gestao, SerieTempo } from "@/lib/api";
import { formatarValor, inicioDaJanela } from "@/lib/descobertas";

export type Dominio = { de: number; ate: number };

export const pos = (d: Dominio, ano: number) => ((ano - d.de + 0.5) / (d.ate - d.de + 1)) * 100;
const borda = (d: Dominio, ano: number) => ((ano - d.de) / (d.ate - d.de + 1)) * 100;

export function nomeCurto(g: Gestao) {
  return g.nome
    .toLowerCase()
    .replace(/(^|\s|-)(\p{L})/gu, (m) => m.toUpperCase())
    .replace(/\b(Da|De|Do|Das|Dos|E)\b/g, (m) => m.toLowerCase());
}

/** Ano em foco compartilhado entre os gráficos de uma tela. */
export function useAnoFoco() {
  return useState<number | null>(null);
}

function anoDoPonteiro(d: Dominio, e: PointerEvent<HTMLElement>): number {
  const r = e.currentTarget.getBoundingClientRect();
  const f = Math.min(0.999, Math.max(0, (e.clientX - r.left) / r.width));
  return d.de + Math.floor(f * (d.ate - d.de + 1));
}

export function FaixasGestao({
  d,
  gestoes,
  cargo,
  selecionada,
  aoEscolher,
  foco,
}: {
  d: Dominio;
  gestoes: Gestao[];
  cargo: string;
  selecionada?: string | null;
  aoEscolher?: (chave: string, g: Gestao) => void;
  foco?: number | null;
}) {
  const visiveis = gestoes.filter((g) => g.fim >= d.de && g.inicio <= d.ate);
  if (visiveis.length === 0) return null;
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted-foreground">
        {cargo}
        {visiveis[0].inicio > d.de ? ` (antes de ${visiveis[0].inicio}: eleição não carregada)` : ""}
      </span>
      <div className="relative h-8" role="group" aria-label={`${cargo} em cada período`}>
        {visiveis.map((g, i) => {
          const a = Math.max(g.inicio, d.de);
          const z = Math.min(g.fim, d.ate);
          const chave = `${cargo}-${g.inicio}`;
          const sel = selecionada === chave;
          const noFoco = foco != null && foco >= g.inicio && foco <= g.fim;
          const estilo = {
            left: `${borda(d, a)}%`,
            width: `${borda(d, z + 1) - borda(d, a)}%`,
            background: sel ? "var(--foreground)" : i % 2 ? "var(--muted)" : "var(--card)",
            color: sel ? "var(--background)" : undefined,
            borderColor: noFoco && !sel ? "var(--foreground)" : undefined,
          };
          const completo = `${cargo}: ${nomeCurto(g)}${g.partido ? ` (${g.partido})` : ""}, ${g.inicio} a ${g.fim}`;
          const texto = (
            <span className="truncate" title={completo}>
              {nomeCurto(g)}
              <span className="hidden lg:inline">{g.partido ? ` (${g.partido})` : ""}</span>
            </span>
          );
          return aoEscolher ? (
            <button
              key={chave}
              type="button"
              aria-pressed={sel}
              aria-label={completo}
              onClick={() => aoEscolher(chave, g)}
              className="absolute top-0 flex h-7 items-center border border-border px-1.5 text-left text-xs hover:border-foreground"
              style={estilo}
            >
              {texto}
            </button>
          ) : (
            <div key={chave} title={completo} className="absolute top-0 flex h-7 items-center border border-border px-1.5 text-xs" style={estilo}>
              {texto}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Coluna à direita para os rótulos do fim da linha; o eixo reserva a mesma para os anos baterem. */
export const COM_COLUNA = "grid grid-cols-[minmax(0,1fr)_5.5rem] gap-2";

export function EixoAnos({ d, foco, reserva = false }: { d: Dominio; foco?: number | null; reserva?: boolean }) {
  const anos = Array.from({ length: d.ate - d.de + 1 }, (_, i) => d.de + i);
  const eixo = (
    <div className="relative h-5 text-xs text-muted-foreground" aria-hidden>
      {anos.map((a, i) => (
        <span
          key={a}
          className={`absolute -translate-x-1/2 tabular-nums ${a === foco ? "font-semibold text-foreground" : i % 2 && a !== d.ate ? "hidden sm:inline" : ""}`}
          style={{ left: `${pos(d, a)}%` }}
        >
          {a === foco ? a : String(a).slice(2)}
        </span>
      ))}
    </div>
  );
  return reserva ? (
    <div className={COM_COLUNA}>
      {eixo}
      <span />
    </div>
  ) : (
    eixo
  );
}

/** Frase curta da série na janela (de quanto para quanto), ou só o último valor. */
export function resumoSerie(s: SerieTempo, d: Dominio): string {
  const pts = s.pontos.filter((p) => p.ano >= d.de && p.ano <= d.ate);
  if (pts.length === 0) return "sem dado no período";
  const fim = pts[pts.length - 1];
  const ini = inicioDaJanela(pts, d.ate - d.de) ?? (pts.length > 1 ? pts[0] : null);
  if (!ini || ini.ano === fim.ano) return `${formatarValor(s, fim.valor)} em ${fim.ano}; anos anteriores sem dado`;
  return `de ${formatarValor(s, ini.valor)} em ${ini.ano} para ${formatarValor(s, fim.valor)} em ${fim.ano}`;
}

const CINZA_ESTADO = "var(--muted-foreground)";

/**
 * Uma série como linha (ou barras, quando é contagem por ano), na sua própria escala, com o menor e
 * o maior valor escritos; estado e Brasil entram em cinza (contínuo e tracejado) quando a unidade é
 * a mesma. Com `foco`, marca o ano e escreve o valor dele; sem foco, escreve o 1º e o último.
 */
export function LinhaSerie({
  d,
  s,
  cor,
  todos = false,
  faixa,
  altura = 72,
  foco = null,
  aoFocar,
  nomeEstado = "estado",
  nomeLugar,
  reserva,
}: {
  d: Dominio;
  s: SerieTempo;
  cor: string;
  todos?: boolean;
  faixa?: { de: number; ate: number } | null;
  altura?: number;
  foco?: number | null;
  aoFocar?: (ano: number | null) => void;
  nomeEstado?: string;
  /** Nome do lugar na legenda e no rótulo do fim da linha (quando há estado e Brasil). */
  nomeLugar?: string;
  /** Reserva a coluna da direita mesmo sem estado e Brasil (para alinhar com outras séries). */
  reserva?: boolean;
}) {
  const pts = s.pontos.filter((p) => p.ano >= d.de && p.ano <= d.ate);
  if (pts.length === 0) return null;
  const comps = s.comparacoes
    .map((c, i) => ({ ...c, pontos: c.pontos.filter((p) => p.ano >= d.de && p.ano <= d.ate), traco: i === 0 && c.rotulo === "estado" ? undefined : "4 3" }))
    .filter((c) => c.pontos.length > 0);
  const vals = [...pts, ...comps.flatMap((c) => c.pontos)].map((p) => p.valor);
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const doZero = s.unidade === "por ano";
  const base = doZero ? 0 : mn - (mx - mn) * 0.12;
  const topo = mx === base ? base + 1 : mx + (mx - base) * 0.08;
  const y = (v: number) => 100 - ((v - base) / (topo - base)) * 100;
  const noFoco = foco != null ? pts.find((p) => p.ano === foco) : undefined;
  const anosComDado = pts.map((p) => p.ano);
  const resumo = pts.map((p) => `${p.ano}: ${formatarValor(s, p.valor)}`).join("; ");
  const anoAtual = foco ?? anosComDado[anosComDado.length - 1];
  const pAtual = pts.find((x) => x.ano === anoAtual);
  const textoDoAno = `${anoAtual}: ${pAtual ? formatarValor(s, pAtual.valor) : "sem dado"}`;

  const teclar = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!aoFocar) return;
    const atual = foco ?? anosComDado[anosComDado.length - 1];
    const i = anosComDado.indexOf(atual);
    let prox: number | null = null;
    if (e.key === "ArrowRight") prox = anosComDado[Math.min(anosComDado.length - 1, (i < 0 ? anosComDado.length - 1 : i) + 1)];
    else if (e.key === "ArrowLeft") prox = anosComDado[Math.max(0, (i < 0 ? 0 : i) - 1)];
    else if (e.key === "Home") prox = anosComDado[0];
    else if (e.key === "End") prox = anosComDado[anosComDado.length - 1];
    else if (e.key === "Escape") prox = null;
    else return;
    e.preventDefault();
    aoFocar(prox);
  };

  const nomeComp = (r: string) => (r === "estado" ? nomeEstado : r);
  // 30 px entre rótulos (cabem duas linhas curtas), em % da altura do gráfico.
  const passo = (30 / altura) * 100;
  const fins = comps.length
    ? [
        { nome: nomeLugar ?? "aqui", v: pts[pts.length - 1].valor, cor, forte: true },
        ...comps.map((c) => ({ nome: nomeComp(c.rotulo), v: c.pontos[c.pontos.length - 1].valor, cor: CINZA_ESTADO, forte: false })),
      ]
        .map((f) => ({ ...f, y: y(f.v) }))
        .sort((a, b) => a.y - b.y)
    : [];
  for (let k = 1; k < fins.length; k++) fins[k].y = Math.max(fins[k].y, fins[k - 1].y + passo);
  if (fins.length) {
    fins[fins.length - 1].y = Math.min(fins[fins.length - 1].y, 100);
    for (let k = fins.length - 2; k >= 0; k--) fins[k].y = Math.min(fins[k].y, fins[k + 1].y - passo);
  }
  const classe = `relative mt-5 ${aoFocar ? "cursor-crosshair touch-pan-y focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze" : ""}`;
  const desenho = (
    <>
        {faixa && (
          <span
            aria-hidden
            className="absolute inset-y-0 opacity-15"
            style={{
              left: `${borda(d, Math.max(faixa.de, d.de))}%`,
              width: `${borda(d, Math.min(faixa.ate, d.ate) + 1) - borda(d, Math.max(faixa.de, d.de))}%`,
              background: "var(--bronze)",
            }}
          />
        )}
        <span aria-hidden className="absolute inset-x-0 top-0 border-t border-dashed border-border" />
        <span aria-hidden className="absolute inset-x-0 bottom-0 border-b border-border" />
        {foco != null && foco >= d.de && foco <= d.ate && (
          <span aria-hidden className="absolute inset-y-0 w-px bg-foreground/60" style={{ left: `${pos(d, foco)}%` }} />
        )}
        {doZero ? (
          pts.map((p) => (
            <span
              key={p.ano}
              aria-hidden
              className="absolute bottom-0 w-[3.2%] -translate-x-1/2"
              style={{
                left: `${pos(d, p.ano)}%`,
                height: `${100 - y(p.valor)}%`,
                background: cor,
                opacity: foco != null && foco !== p.ano ? 0.45 : 1,
              }}
            />
          ))
        ) : (
          <svg aria-hidden className="absolute inset-0 size-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
            {comps.map((c) => (
              <polyline
                key={c.rotulo}
                fill="none"
                stroke={CINZA_ESTADO}
                strokeWidth={1.5}
                strokeDasharray={c.traco}
                vectorEffect="non-scaling-stroke"
                points={c.pontos.map((p) => `${pos(d, p.ano)},${y(p.valor)}`).join(" ")}
              />
            ))}
            <polyline
              fill="none"
              stroke={cor}
              strokeWidth={2.5}
              vectorEffect="non-scaling-stroke"
              points={pts.map((p) => `${pos(d, p.ano)},${y(p.valor)}`).join(" ")}
            />
          </svg>
        )}
        {!doZero &&
          pts.map((p) => (
            <span
              key={p.ano}
              aria-hidden
              className="absolute -translate-x-1/2 translate-y-1/2 rounded-full ring-2 ring-[var(--background)]"
              style={{
                left: `${pos(d, p.ano)}%`,
                bottom: `${100 - y(p.valor)}%`,
                background: cor,
                width: p.ano === foco ? 12 : 8,
                height: p.ano === foco ? 12 : 8,
              }}
            />
          ))}
        {pts.map((p, i) => {
          const mostrar = foco != null ? p.ano === foco : todos || i === 0 || (i === pts.length - 1 && comps.length === 0);
          if (!mostrar) return null;
          const lado = pos(d, p.ano) < 12 ? "-translate-x-1" : pos(d, p.ano) > 88 ? "-translate-x-full" : "-translate-x-1/2";
          return (
            <span
              key={p.ano}
              aria-hidden
              className={`absolute ${lado} text-xs whitespace-nowrap tabular-nums ${p.ano === foco ? "rounded-[2px] bg-foreground px-1 font-semibold text-background" : "text-foreground"}`}
              style={{ left: `${pos(d, p.ano)}%`, bottom: `calc(${100 - y(p.valor)}% + 7px)` }}
            >
              {formatarValor(s, p.valor)}
            </span>
          );
        })}
        {foco != null && !noFoco && foco >= d.de && foco <= d.ate && (
          <span
            aria-hidden
            className="absolute top-1/2 -translate-x-1/2 text-[0.65rem] whitespace-nowrap text-muted-foreground"
            style={{ left: `${pos(d, foco)}%` }}
          >
            sem dado
          </span>
        )}
    </>
  );
  const grafico = aoFocar ? (
        <div
          className={classe}
          style={{ height: altura }}
          role="slider"
          aria-label={`${s.rotulo}, ano a ano. Setas mudam o ano.`}
          aria-valuemin={anosComDado[0]}
          aria-valuemax={anosComDado[anosComDado.length - 1]}
          aria-valuenow={anoAtual}
          aria-valuetext={textoDoAno}
          tabIndex={0}
          onKeyDown={teclar}
          onPointerMove={(e) => aoFocar(anoDoPonteiro(d, e))}
          onPointerDown={(e) => aoFocar(anoDoPonteiro(d, e))}
          onPointerLeave={(e) => e.pointerType === "mouse" && aoFocar(null)}
        >
          {desenho}
        </div>
      ) : (
        <div className={classe} style={{ height: altura }} role="img" aria-label={`${s.rotulo}. ${resumo}`}>
          {desenho}
        </div>
      );
  const escala = (
    <p className="text-[0.7rem] text-muted-foreground tabular-nums" aria-hidden>
      Escala: de {formatarValor(s, doZero ? 0 : mn)} a {formatarValor(s, mx)}
    </p>
  );
  if (comps.length === 0)
    return (
      <figure className="m-0">
        {escala}
        {reserva ? (
          <div className={COM_COLUNA}>
            {grafico}
            <span />
          </div>
        ) : (
          grafico
        )}
      </figure>
    );
  return (
    <figure className="m-0">
      {escala}
      <ul className="flex flex-wrap gap-x-4 text-xs text-muted-foreground" aria-hidden>
        <li className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5" style={{ background: cor }} /> {nomeLugar ?? "aqui"}
        </li>
        {comps.map((c) => (
          <li key={c.rotulo} className="flex items-center gap-1.5">
            <span className="inline-block w-5 border-t-2" style={{ borderColor: CINZA_ESTADO, borderStyle: c.traco ? "dashed" : "solid" }} />
            {nomeComp(c.rotulo)}
          </li>
        ))}
      </ul>
      <div className={COM_COLUNA}>
        {grafico}
        <div className="relative mt-5" style={{ height: altura }} aria-hidden>
          {fins.map((f) => (
            <span
              key={f.nome}
              className={`absolute right-0 left-0 -translate-y-1/2 text-xs leading-tight tabular-nums ${f.forte ? "font-semibold text-foreground" : "text-muted-foreground"}`}
              style={{ top: `${f.y}%` }}
            >
              <span className="block truncate">{f.nome}</span>
              <span className="block">{formatarValor(s, f.v)}</span>
            </span>
          ))}
        </div>
      </div>
    </figure>
  );
}

/** O que acontecia no ano em foco: quem governava e o valor de cada série (estado e Brasil juntos). */
export function PainelAno({
  ano,
  series,
  gestoes,
  nomeEstado,
}: {
  ano: number | null;
  series: SerieTempo[];
  gestoes: { prefeito?: Gestao[]; governador?: Gestao[] };
  nomeEstado: string;
}) {
  if (ano == null) {
    return (
      <p className="text-sm text-muted-foreground" aria-live="polite">
        Passe o dedo ou o mouse sobre um gráfico (ou use as setas do teclado) para ver um ano.
      </p>
    );
  }
  const quem = (lista: Gestao[] | undefined, cargo: string) => {
    const g = lista?.find((x) => ano >= x.inicio && ano <= x.fim);
    return g ? `${cargo}: ${nomeCurto(g)}${g.partido ? ` (${g.partido})` : ""}` : null;
  };
  const governo = [quem(gestoes.prefeito, "Prefeito"), quem(gestoes.governador, "Governador")].filter(Boolean);
  return (
    <div className="border border-l-4 border-border bg-card p-3 text-sm" style={{ borderLeftColor: "var(--bronze)" }} aria-live="polite">
      <p className="numero text-lg">{ano}</p>
      {governo.length > 0 && <p className="text-muted-foreground">{governo.join(" · ")}</p>}
      <ul className="mt-1 grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
        {series.map((s) => {
          const p = s.pontos.find((x) => x.ano === ano);
          const comps = s.comparacoes
            .map((c) => {
              const v = c.pontos.find((x) => x.ano === ano);
              return v ? `${c.rotulo === "estado" ? nomeEstado : c.rotulo}: ${formatarValor(s, v.valor)}` : null;
            })
            .filter(Boolean);
          return (
            <li key={s.id}>
              <span className="text-muted-foreground">{s.rotulo}:</span>{" "}
              <b className="font-semibold tabular-nums">{p ? formatarValor(s, p.valor) : "sem dado"}</b>
              {p && comps.length > 0 && <span className="text-muted-foreground"> ({comps.join("; ")})</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
