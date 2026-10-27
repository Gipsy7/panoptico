import type { ParlamentarResumo } from "@/lib/api";

/**
 * Desenho do panóptico (torre central e anel de celas), sem estado próprio: quem o usa escolhe
 * o `estado` (0 a 5) e, se quiser, os parlamentares que aparecem dentro da torre de vidro.
 * Serve à história de /o-panoptico (cliente) e à seção da página inicial (servidor).
 *
 *  0 a cela: uma cela em destaque e o feixe da torre, cuja janela é escura
 *  1 Bentham: o anel completo, raios da torre para todas as celas
 *  2 Foucault: setas mostram todas as figuras olhando para a torre, que aparece vazia
 *  3 inversão: torre de vidro, raios das celas para a torre, parlamentares dentro (com zoom)
 *  4 e 5: o mesmo, sem zoom
 *
 * Cores só por tokens do tema. As transições respeitam prefers-reduced-motion.
 */
export type EstadoPanoptico = 0 | 1 | 2 | 3 | 4 | 5;

export const DESCRICOES_PANOPTICO: Record<EstadoPanoptico, string> = {
  0: "Desenho de um anel de celas em volta de uma torre. Uma cela, a sua, está em destaque, iluminada por um feixe de luz que sai da torre. A janela da torre é escura.",
  1: "Desenho de um anel completo de celas em volta de uma torre opaca. Raios saem da torre em direção a todas as celas.",
  2: "Desenho do anel de celas. Todas as figuras olham para a torre, que está vazia.",
  3: "Aproximação na torre, agora transparente. Dentro dela aparecem representantes eleitos, e os raios vão das celas para a torre.",
  4: "Desenho do anel de celas em volta de uma torre transparente. Os raios saem das celas, que são os cidadãos, em direção à torre, onde estão os representantes.",
  5: "Desenho do anel de celas em volta de uma torre transparente. Os raios saem das celas, que são os cidadãos, em direção à torre, onde estão os representantes.",
};

const CENTRO = 160;
const N = 12;
const VOCE = 6; // a cela de baixo
// Posições (relativas ao centro) dos três lugares dentro da torre.
const LUGARES = [
  { x: 0, y: -21 },
  { x: -19, y: 13 },
  { x: 19, y: 13 },
];

const r2 = (n: number) => Math.round(n * 100) / 100;
function ponto(raio: number, graus: number) {
  const a = (graus * Math.PI) / 180;
  return { x: r2(CENTRO + raio * Math.cos(a)), y: r2(CENTRO + raio * Math.sin(a)) };
}

const CELAS = Array.from({ length: N }, (_, i) => {
  const graus = i * (360 / N) - 90;
  return { i, graus, centro: ponto(124, graus), de: ponto(104, graus), ate: ponto(58, graus) };
});

// Feixe de luz da torre até a cela do leitor (um trapézio).
const FEIXE = (() => {
  const g = CELAS[VOCE].graus;
  const a = ponto(48, g - 9);
  const b = ponto(48, g + 9);
  const c = ponto(108, g + 6);
  const d = ponto(108, g - 6);
  return `M${a.x} ${a.y}L${d.x} ${d.y}L${c.x} ${c.y}L${b.x} ${b.y}z`;
})();

const TRANSICAO = "transition-opacity duration-700 motion-reduce:transition-none";
const mostra = (v: boolean) => (v ? "opacity-100" : "opacity-0");

export type PessoaNaTorre = ParlamentarResumo;

export function PanopticoDesenho({
  estado,
  pessoas = [],
  selecionado = null,
  onSelecionar,
  idBase = "pan",
  className = "",
  zoom: comZoom = true,
  animar = true,
}: {
  estado: EstadoPanoptico;
  pessoas?: PessoaNaTorre[];
  selecionado?: number | null;
  onSelecionar?: (indice: number) => void;
  idBase?: string;
  className?: string;
  /** Aproxima a torre no estado 3, só em telas de 1024 px ou mais (no celular o desenho já é pequeno). */
  zoom?: boolean;
  /** false desliga as transições (primeiro quadro da história, para não animar ao carregar). */
  animar?: boolean;
}) {
  const T = animar ? TRANSICAO : "";
  const vidro = estado >= 3;
  const zoom = comZoom && estado === 3;
  const opaca = estado <= 2;

  return (
    <svg viewBox="0 0 320 320" role="img" aria-label={DESCRICOES_PANOPTICO[estado]} className={`text-foreground ${className}`}>
      <defs>
        <marker id={`${idBase}-cela`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 1l9 4-9 4z" className="fill-muted-foreground" />
        </marker>
        <marker id={`${idBase}-torre`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 1l9 4-9 4z" className="fill-bronze" />
        </marker>
        {LUGARES.map((_, k) => (
          <clipPath key={k} id={`${idBase}-av-${k}`}>
            <circle r="15" />
          </clipPath>
        ))}
      </defs>

      <g
        className={`origin-[160px_160px] ${animar ? "transition-transform duration-1000 ease-out motion-reduce:transition-none" : ""} ${zoom ? "lg:scale-[1.75]" : ""}`}
      >
        <circle cx={CENTRO} cy={CENTRO} r="146" className="fill-none stroke-border" strokeWidth="1" />

        {/* Estado 0: o feixe da torre sobre a cela do leitor. */}
        <path d={FEIXE} className={`fill-bronze/30 stroke-bronze ${T} ${mostra(estado === 0)}`} strokeWidth="1" />

        {/* Raios da torre para as celas (Bentham e Foucault). */}
        <g aria-hidden className={`${T} ${mostra(estado === 1 || estado === 2)}`}>
          {CELAS.map((c) => (
            <line key={c.i} x1={c.ate.x} y1={c.ate.y} x2={c.de.x} y2={c.de.y} className="stroke-muted-foreground" strokeWidth="1.5" markerEnd={`url(#${idBase}-cela)`} />
          ))}
        </g>

        {/* Raios das celas para a torre (inversão). */}
        <g aria-hidden className={`${T} ${mostra(vidro)}`}>
          {CELAS.map((c) => (
            <line key={c.i} x1={c.de.x} y1={c.de.y} x2={c.ate.x} y2={c.ate.y} className="stroke-bronze" strokeWidth="1.5" markerEnd={`url(#${idBase}-torre)`} />
          ))}
        </g>

        {/* Celas e as pessoas dentro delas. */}
        {CELAS.map((c) => {
          const apagada = estado === 0 && c.i !== VOCE;
          const luz = estado === 0 ? c.i === VOCE : estado === 1 || estado === 2;
          return (
            // Cela e figura ficam sempre em pé (girar com o anel deixava a figura de lado ou de
            // cabeça para baixo); só a seta do olhar gira para apontar a torre.
            <g key={c.i} transform={`translate(${c.centro.x} ${c.centro.y})`} className={`${T} ${apagada ? "opacity-30" : "opacity-100"}`}>
              <rect x="-12" y="-12" width="24" height="24" rx="1" className="fill-card stroke-foreground" strokeWidth="1.5" />
              <rect x="-12" y="-12" width="24" height="24" rx="1" className={`fill-bronze ${T} ${luz ? "opacity-35" : "opacity-0"}`} />
              {/* Figura reta e centrada na cela (cabeça de -7 a 0, corpo de 1 a 7.5). */}
              <circle cx="0" cy="-3.5" r="3.5" className="fill-foreground" />
              <path d="M-6.5 7.5a6.5 6.5 0 0 1 13 0z" className="fill-foreground" />
              {/* Olhar para a torre (Foucault). */}
              <g transform={`rotate(${c.graus + 90})`}>
                <path d="M-3.5 19L0 23L3.5 19" className={`fill-none stroke-bronze ${T} ${mostra(estado === 2)}`} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </g>
            </g>
          );
        })}

        {/* Legenda da cela do leitor. */}
        <text x="178" y="289" textAnchor="start" className={`fill-bronze-texto text-[13px] font-semibold ${T} ${mostra(estado === 0)}`}>
          você
        </text>

        {/* Torre opaca. */}
        <circle cx={CENTRO} cy={CENTRO} r="48" className={`fill-foreground ${T} ${mostra(opaca)}`} />
        {/* Janela: escura no começo, acesa e vazia no passo de Foucault. */}
        <rect x="150" y="147" width="20" height="26" rx="1" className={`fill-background ${T} ${estado === 2 ? "opacity-100" : estado <= 1 ? "opacity-20" : "opacity-0"}`} />

        {/* Torre de vidro. */}
        <g className={`${T} ${mostra(vidro)}`}>
          <circle cx={CENTRO} cy={CENTRO} r="48" className="fill-background stroke-bronze" strokeWidth="2" strokeDasharray="5 4" />
          {LUGARES.map((l, k) => {
            const p = pessoas[k];
            const sel = selecionado === k;
            return (
              <g
                key={k}
                transform={`translate(${CENTRO + l.x} ${CENTRO + l.y})`}
                onClick={onSelecionar && p ? () => onSelecionar(k) : undefined}
                className={onSelecionar && p ? "cursor-pointer" : undefined}
              >
                {p ? (
                  <>
                    <circle r="15" className="fill-muted" />
                    {p.foto_url && (
                      <image
                        href={p.foto_url}
                        x="-15"
                        y="-15"
                        width="30"
                        height="30"
                        preserveAspectRatio="xMidYMin slice"
                        clipPath={`url(#${idBase}-av-${k})`}
                      />
                    )}
                    <circle r="15" className={`fill-none ${sel ? "stroke-bronze" : "stroke-foreground"}`} strokeWidth={sel ? 3 : 1} />
                  </>
                ) : (
                  <g className="fill-none stroke-foreground" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <Icone k={k} />
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </g>
    </svg>
  );
}

/** Gasto (moeda), voto (urna) e projeto (folha): ícones simples para a torre sem rostos. */
function Icone({ k }: { k: number }) {
  if (k === 0) {
    return (
      <>
        <circle r="9" />
        <path d="M-3.5 -3h5a2.2 2.2 0 0 1 0 4.4h-3.4a2.2 2.2 0 0 0 0 4.4H3.5" strokeWidth="1.3" />
      </>
    );
  }
  if (k === 1) return <path d="M-9 3h18v7h-18zM-4.5 3v-9h9v9M-2 -2l1.8 1.8 2.9-3.4" />;
  return <path d="M-7 -10h9l5 5v15h-14zM2 -10v5h5M-3 1h7M-3 6h7" />;
}
