"use client";

// Mão "TOQUE" que convida a tocar: ondas e dedo animados (SMIL), etiqueta ao lado.
// Desenhada em coordenadas de SVG, com a ponta do dedo em (0, 0) do grupo; quem usa
// posiciona com x/y. Com prefers-reduced-motion fica parada e sem ondas.

import { useSyncExternalStore } from "react";

export function useMovimentoReduzido() {
  return useSyncExternalStore(
    (aviso) => {
      const m = window.matchMedia("(prefers-reduced-motion: reduce)");
      m.addEventListener("change", aviso);
      return () => m.removeEventListener("change", aviso);
    },
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
}

export function MaoToque({
  x,
  y,
  oculta,
  reduzido,
  etiquetaEsquerda,
  semEtiqueta = false,
}: {
  x: number;
  y: number;
  /** Some (opacidade 0) depois do primeiro toque. */
  oculta: boolean;
  reduzido: boolean;
  /** Etiqueta à esquerda do dedo, para não sair do desenho. */
  etiquetaEsquerda: boolean;
  /** Sem a etiqueta "TOQUE" (quando o alvo já diz o que fazer, como um botão). */
  semEtiqueta?: boolean;
}) {
  return (
    <g
      aria-hidden="true"
      className="pointer-events-none transition-[transform,opacity] duration-700 ease-in-out motion-reduce:transition-none"
      style={{
        transform: `translate(${x}px, ${y}px)`,
        opacity: oculta ? 0 : 1,
      }}
    >
      {!reduzido &&
        [0, 0.5].map((atraso) => (
          <circle
            key={atraso}
            className="fill-none stroke-bronze"
            strokeWidth={2.5}
            r={16}
          >
            <animate
              attributeName="r"
              from="6"
              to="27"
              dur="1.6s"
              begin={`${atraso}s`}
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              from="0.9"
              to="0"
              dur="1.6s"
              begin={`${atraso}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      <g transform="translate(-3.2 19)">
        <path
          className="fill-background stroke-foreground"
          strokeWidth={1.6}
          strokeLinejoin="round"
          d="M0 0V-16a3.2 3.2 0 0 1 6.4 0V-4l2-.6a3 3 0 0 1 3.6 2.2l.2.9 1.6-.3a3 3 0 0 1 3.4 2.4L18 6c.6 4-1.8 9-6.8 9H6c-2.4 0-4.2-1.2-5.4-3L-5 4.6a2.6 2.6 0 0 1 3.8-3.5z"
        >
          {!reduzido && (
            <animateTransform
              attributeName="transform"
              type="translate"
              values="0 0; -2 -5; 0 0; 0 0"
              keyTimes="0; 0.45; 0.6; 1"
              dur="1.6s"
              repeatCount="indefinite"
            />
          )}
        </path>
      </g>
      {!semEtiqueta && (
        <>
          <rect
            className="fill-background stroke-bronze"
            strokeWidth={1}
            x={etiquetaEsquerda ? -76 : 24}
            y={-22}
            width={52}
            height={20}
            rx={10}
          />
          <text
            className="fill-bronze-texto text-[12px] font-semibold tracking-[0.06em]"
            x={etiquetaEsquerda ? -50 : 50}
            y={-8}
            textAnchor="middle"
          >
            TOQUE
          </text>
        </>
      )}
    </g>
  );
}
