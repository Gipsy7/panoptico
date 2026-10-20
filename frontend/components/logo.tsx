/**
 * Marca do Panóptico: o panóptico invertido.
 *
 * No panóptico original, um vigia na torre central vê todas as celas em volta. Aqui as
 * "celas" (os traços do anel) é que olham para o centro, e a torre virou um círculo
 * vazado: o poder, transparente, sob o olhar de todos.
 *
 * SVG puro com currentColor (herda a cor do texto). A animação de desenho é só CSS
 * (classe .logo-animada em globals.css) e respeita prefers-reduced-motion.
 */

import {
  CAMINHO_NOME,
  CAMINHO_SOCIAL,
  LOGO_ALTURA,
  LOGO_LARGURA,
  LOGO_SOL,
  LOGO_VIEWBOX,
} from "@/lib/logo-caminhos";

const TRACOS = 12;
const RAIO_EXTERNO = 28;
const RAIO_INTERNO = 15;

// Coordenadas arredondadas para o SVG sair idêntico no servidor e no navegador.
const r = (n: number) => Math.round(n * 100) / 100;
const LINHAS = Array.from({ length: TRACOS }, (_, i) => {
  const angulo = (i / TRACOS) * 2 * Math.PI - Math.PI / 2;
  const cos = Math.cos(angulo);
  const sen = Math.sin(angulo);
  // Desenhada de fora para dentro: o traço "olha" para a torre.
  return {
    x1: r(32 + RAIO_EXTERNO * cos),
    y1: r(32 + RAIO_EXTERNO * sen),
    x2: r(32 + RAIO_INTERNO * cos),
    y2: r(32 + RAIO_INTERNO * sen),
  };
});

export function Marca({
  tamanho = 32,
  animada = false,
  className = "",
  titulo,
  traco = 3.2,
}: {
  tamanho?: number;
  animada?: boolean;
  className?: string;
  titulo?: string;
  /** Espessura do traço em unidades do desenho (64×64). Em tamanhos grandes, use fino. */
  traco?: number;
}) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={tamanho}
      height={tamanho}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      className={`${animada ? "logo-animada" : ""} ${className}`}
      role={titulo ? "img" : undefined}
      aria-hidden={titulo ? undefined : true}
      aria-label={titulo}
    >
      {LINHAS.map((l, i) => (
        <line
          key={i}
          {...l}
          strokeWidth={traco}
          style={animada ? { animationDelay: `${i * 45}ms` } : undefined}
        />
      ))}
      <circle cx={32} cy={32} r={7.5} strokeWidth={traco * 0.8} className="logo-torre" />
    </svg>
  );
}

export function Logo({ animada = false, tamanho = 30 }: { animada?: boolean; tamanho?: number }) {
  // `tamanho` é a altura do sol; o nome e o ".social" vêm da arte oficial (lib/logo-caminhos.ts).
  const escala = tamanho / LOGO_ALTURA;
  return (
    <svg
      viewBox={LOGO_VIEWBOX}
      width={Math.round(LOGO_LARGURA * escala * 100) / 100}
      height={tamanho}
      role="img"
      aria-label="Panóptico.social"
      className="text-marca-nome"
    >
      <path d={CAMINHO_NOME} fill="currentColor" />
      <path d={CAMINHO_SOCIAL} className="fill-bronze-texto" />
      <g
        transform={`translate(${LOGO_SOL.cx} ${LOGO_SOL.cy}) scale(${LOGO_SOL.escala}) translate(-32 -32)`}
        fill="none"
        strokeLinecap="round"
        strokeWidth={2.3}
        className={`stroke-bronze ${animada ? "logo-animada" : ""}`}
      >
        {LINHAS.map((l, i) => (
          <line
            key={i}
            {...l}
            style={animada ? { animationDelay: `${i * 45}ms` } : undefined}
          />
        ))}
        <circle cx={32} cy={32} r={7.5} strokeWidth={1.9} className="logo-torre" />
      </g>
    </svg>
  );
}
