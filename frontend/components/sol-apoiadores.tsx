"use client";

import { useState } from "react";

export type Apoiador = { nome: string; desde?: string };

const C = 320; // centro do desenho (640 x 640)
const R_TORRE = 34;
const r2 = (n: number) => Math.round(n * 100) / 100;

/** Nome curto o bastante para caber ao longo do raio; o nome inteiro está na lista e na legenda. */
function abreviar(nome: string, max: number) {
  return nome.length > max ? `${nome.slice(0, max - 1).trimEnd()}…` : nome;
}

/**
 * O sol da marca com um raio por apoiador. No computador o nome vai escrito ao longo do raio; no
 * celular, onde não cabe legível, só os raios aparecem e os nomes ficam na lista logo abaixo,
 * ligados ao raio pelo destaque. Com mais de 24 nomes os raios se alternam em dois comprimentos.
 * Os raios são decorativos (aria-hidden); a lista de botões é o caminho por teclado e leitor de tela.
 */
export function SolApoiadores({ apoiadores }: { apoiadores: Apoiador[] }) {
  const [ativo, setAtivo] = useState<number | null>(null);
  const n = apoiadores.length;
  // O sol é sempre completo: no mínimo os 12 raios da marca; passando disso, um raio por nome.
  const total = Math.max(12, n);
  const dois = total > 24;
  const fonte = n > 40 ? 11 : 13.5;
  const maxCaracteres = n > 40 ? 28 : 24;
  const atual = ativo !== null ? apoiadores[ativo] : null;
  const comprimento = (i: number) => (dois && i % 2 === 1 ? 96 : 138);

  // Nomes espalhados pelos raios (não vizinhos), começando meio passo depois do alto.
  const acesos = new Map<number, number>(); // raio -> índice do apoiador
  apoiadores.forEach((_, k) => acesos.set(Math.floor((k * total) / n), k));

  // Tamanho do desenho: no computador, até o fim do maior nome escrito; no celular, só até a ponta dos raios.
  const alcance = apoiadores.map((a, k) => {
    const i = Math.floor((k * total) / n);
    const dist = comprimento(i) + 12 + abreviar(a.nome, maxCaracteres).length * fonte * 0.56;
    const ang = (((i + 0.5) / total) * 360 - 90) * (Math.PI / 180);
    return Math.max(Math.abs(dist * Math.cos(ang)), Math.abs(dist * Math.sin(ang)));
  });
  const R = Math.min(318, Math.ceil(Math.max(150, ...alcance) + 14)); // metade do lado, no computador
  const Rm = 150; // metade do lado, no celular
  const estilo = {
    "--larg": `${r2((R / Rm) * 100)}%`,
    "--desloc": `${r2(((R - Rm) / (2 * Rm)) * 100)}%`,
  } as React.CSSProperties;

  return (
    <div className="flex flex-col gap-4">
      {/* No celular, sem os nomes, o desenho é recortado em volta do sol para os raios não ficarem pequenos. */}
      <div className="mx-auto aspect-square w-full max-w-[34rem] overflow-hidden" style={estilo}>
        <svg
          viewBox={`${C - R} ${C - R} ${2 * R} ${2 * R}`}
          aria-hidden
          className="mt-[calc(var(--desloc)*-1)] ml-[calc(var(--desloc)*-1)] block h-auto w-[var(--larg)] max-w-none text-foreground md:m-0 md:w-full"
        >
          <circle cx={C} cy={C} r={R_TORRE + 14} className="fill-bronze opacity-10" />
          <circle cx={C} cy={C} r={R_TORRE} className="fill-bronze/15 stroke-bronze" strokeWidth="5" style={{ filter: "drop-shadow(0 0 8px var(--bronze))" }} />
          {Array.from({ length: total }, (_, i) => {
            const theta = ((i + 0.5) / total) * 360; // 0 = para cima, sentido horário
            const k = acesos.get(i);
            const fim = comprimento(i);
            const inicio = R_TORRE + 14;
            return (
              <g key={i} transform={`translate(${C} ${C}) rotate(${r2(theta - 90)})`}>
                {k === undefined ? (
                  <line x1={inicio} y1="0" x2={fim} y2="0" strokeLinecap="round" strokeWidth="2.5" className="stroke-border" />
                ) : (
                  <Raio
                    nome={abreviar(apoiadores[k].nome, maxCaracteres)}
                    inicio={inicio}
                    fim={fim}
                    virado={theta > 180}
                    fonte={fonte}
                    destaque={ativo === k}
                    algumAtivo={ativo !== null}
                    atraso={k * 60}
                    aoEntrar={() => setAtivo(k)}
                    aoSair={() => setAtivo((v) => (v === k ? null : v))}
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <p aria-live="polite" className="min-h-6 text-center text-sm text-muted-foreground">
        {atual ? (
          <>
            <span className="font-semibold text-foreground">{atual.nome}</span>
            {atual.desde && <> · apoia desde {atual.desde}</>}
          </>
        ) : (
          "Passe o mouse ou toque num raio ou num nome."
        )}
      </p>

      <ul className="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
        {apoiadores.map((a, i) => (
          <li key={a.nome} className="border-t border-border">
            <button
              type="button"
              onClick={() => setAtivo(i)}
              onFocus={() => setAtivo(i)}
              onMouseEnter={() => setAtivo(i)}
              aria-pressed={ativo === i}
              className={`flex min-h-11 w-full items-center gap-2 py-2 text-left transition-colors duration-300 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-bronze motion-reduce:transition-none ${ativo === i ? "font-semibold text-foreground" : ""}`}
            >
              <span aria-hidden className={`size-2 shrink-0 rounded-full ${ativo === i ? "bg-bronze" : "bg-border"}`} />
              <span className="flex flex-col">
                <span>{a.nome}</span>
                {a.desde && <span className="text-sm font-normal text-muted-foreground">desde {a.desde}</span>}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Raio({
  nome,
  inicio,
  fim,
  virado,
  fonte,
  destaque,
  algumAtivo,
  atraso,
  aoEntrar,
  aoSair,
}: {
  nome: string;
  inicio: number;
  fim: number;
  virado: boolean;
  fonte: number;
  destaque: boolean;
  algumAtivo: boolean;
  atraso: number;
  aoEntrar: () => void;
  aoSair: () => void;
}) {
  const inicioTexto = fim + 12;
  return (
    <g onMouseEnter={aoEntrar} onMouseLeave={aoSair} onClick={aoEntrar} className="cursor-pointer" style={destaque ? { filter: "drop-shadow(0 0 5px var(--bronze))" } : undefined}>
      {/* Área de toque mais larga que o traço. */}
      <line x1={inicio} y1="0" x2={fim} y2="0" stroke="transparent" strokeWidth="22" />
      <line
        x1={inicio}
        y1="0"
        x2={fim}
        y2="0"
        strokeLinecap="round"
        strokeWidth={destaque ? 6 : 4}
        className={`sol-raio stroke-bronze transition-[stroke-width,opacity] duration-300 motion-reduce:transition-none ${algumAtivo && !destaque ? "opacity-45" : "opacity-100"}`}
        style={{ "--len": fim - inicio, "--atraso": `${atraso}ms` } as React.CSSProperties}
      />
      <text
        x={virado ? -inicioTexto : inicioTexto}
        y="4.5"
        textAnchor={virado ? "end" : "start"}
        transform={virado ? "rotate(180)" : undefined}
        fontSize={fonte}
        className={`sol-nome hidden md:block ${destaque ? "fill-foreground font-semibold" : "fill-muted-foreground"}`}
        style={{ "--atraso": `${400 + atraso}ms` } as React.CSSProperties}
      >
        {nome}
      </text>
    </g>
  );
}
