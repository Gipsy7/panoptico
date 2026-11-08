/**
 * Peças da linha do tempo (protótipos B e C): faixas de gestão, uma linha por série e o eixo de
 * anos, todas no mesmo domínio de anos. Os textos são HTML posicionado em %, e o SVG só desenha a
 * linha (sem distorcer letra), para caber em 320 px sem rolagem lateral.
 */
import type { Gestao, SerieTempo } from "@/lib/api";
import { formatarValor } from "@/lib/descobertas";

export type Dominio = { de: number; ate: number };

export const pos = (d: Dominio, ano: number) => ((ano - d.de + 0.5) / (d.ate - d.de + 1)) * 100;
const borda = (d: Dominio, ano: number) => ((ano - d.de) / (d.ate - d.de + 1)) * 100;

export function nomeCurto(g: Gestao) {
  return g.nome
    .toLowerCase()
    .replace(/(^|\s|-)(\p{L})/gu, (m) => m.toUpperCase())
    .replace(/\b(Da|De|Do|Das|Dos|E)\b/g, (m) => m.toLowerCase());
}

export function FaixasGestao({
  d,
  gestoes,
  cargo,
  selecionada,
  aoEscolher,
}: {
  d: Dominio;
  gestoes: Gestao[];
  cargo: string;
  selecionada?: string | null;
  aoEscolher?: (chave: string, g: Gestao) => void;
}) {
  const visiveis = gestoes.filter((g) => g.fim >= d.de && g.inicio <= d.ate);
  if (visiveis.length === 0) return null;
  return (
    <div className="flex flex-col">
    <span className="text-xs text-muted-foreground">{cargo}</span>
    <div className="relative h-8" role="group" aria-label={`${cargo} em cada período`}>
      {visiveis.map((g, i) => {
        const a = Math.max(g.inicio, d.de);
        const z = Math.min(g.fim, d.ate);
        const chave = `${cargo}-${g.inicio}`;
        const sel = selecionada === chave;
        const estilo = {
          left: `${borda(d, a)}%`,
          width: `${borda(d, z + 1) - borda(d, a)}%`,
          background: sel ? "var(--foreground)" : i % 2 ? "var(--muted)" : "var(--card)",
          color: sel ? "var(--background)" : undefined,
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

export function EixoAnos({ d }: { d: Dominio }) {
  const anos = Array.from({ length: d.ate - d.de + 1 }, (_, i) => d.de + i);
  return (
    <div className="relative h-5 text-xs text-muted-foreground" aria-hidden>
      {anos.map((a, i) => (
        <span
          key={a}
          className={`absolute -translate-x-1/2 tabular-nums ${i % 2 && a !== d.ate ? "hidden sm:inline" : ""}`}
          style={{ left: `${pos(d, a)}%` }}
        >
          {String(a).slice(2)}
        </span>
      ))}
    </div>
  );
}

/** Uma série como linha com pontos, na sua própria escala; rótulo de valor no 1º e no último ponto
 *  (ou em todos, com `todos`). `faixa` sombreia um período (a gestão escolhida). */
export function LinhaSerie({
  d,
  s,
  cor,
  todos = false,
  faixa,
  altura = 64,
}: {
  d: Dominio;
  s: SerieTempo;
  cor: string;
  todos?: boolean;
  faixa?: { de: number; ate: number } | null;
  altura?: number;
}) {
  const pts = s.pontos.filter((p) => p.ano >= d.de && p.ano <= d.ate);
  if (pts.length === 0) return null;
  const vals = pts.map((p) => p.valor);
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  // Barras de contagem começam no zero; o resto usa a faixa dos próprios valores (dito no rótulo).
  const doZero = s.unidade === "por ano";
  const base = doZero ? 0 : mn - (mx - mn) * 0.15;
  const topo = mx === base ? base + 1 : mx;
  const y = (v: number) => 100 - ((v - base) / (topo - base)) * 100;
  const resumo = pts.map((p) => `${p.ano}: ${formatarValor(s, p.valor)}`).join("; ");
  return (
    <figure className="m-0">
      <div className="relative mt-5" style={{ height: altura }} role="img" aria-label={`${s.rotulo}. ${resumo}`}>
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
        <span aria-hidden className="absolute inset-x-0 bottom-0 border-b border-border" />
        {doZero ? (
          pts.map((p) => (
            <span
              key={p.ano}
              aria-hidden
              className="absolute bottom-0 w-[3%] -translate-x-1/2"
              style={{ left: `${pos(d, p.ano)}%`, height: `${100 - y(p.valor)}%`, background: cor }}
            />
          ))
        ) : (
          <svg aria-hidden className="absolute inset-0 size-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke={cor}
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              points={pts.map((p) => `${pos(d, p.ano)},${y(p.valor)}`).join(" ")}
            />
          </svg>
        )}
        {pts.map((p, i) => {
          const mostrar = todos || i === 0 || i === pts.length - 1;
          return (
            <span key={p.ano} aria-hidden>
              {!doZero && (
                <span
                  className="absolute size-2 -translate-x-1/2 translate-y-1/2 rounded-full"
                  style={{ left: `${pos(d, p.ano)}%`, bottom: `${100 - y(p.valor)}%`, background: cor }}
                />
              )}
              {mostrar && (
                <span
                  className={`absolute text-[0.7rem] whitespace-nowrap tabular-nums text-foreground ${
                    i === 0 && pos(d, p.ano) < 12 ? "-translate-x-1" : i === pts.length - 1 && pos(d, p.ano) > 88 ? "-translate-x-full" : "-translate-x-1/2"
                  }`}
                  style={{ left: `${pos(d, p.ano)}%`, bottom: `calc(${100 - y(p.valor)}% + 6px)` }}
                >
                  {formatarValor(s, p.valor)}
                </span>
              )}
            </span>
          );
        })}
      </div>
    </figure>
  );
}
