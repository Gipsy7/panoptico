"use client";

import { useEffect, useRef, useState } from "react";

export type Apoiador = { nome: string; desde?: string };

const C = 320; // centro do desenho (640 x 640)
const R_TORRE = 34;
const R_OLHO = 138; // distância do olho ao centro
const R_OLHO_CURTO = 104; // com mais de 24 olhos, alternados, para não encostarem
const r2 = (n: number) => Math.round(n * 100) / 100;

/** Nome curto o bastante para caber ao longo do olhar; o nome inteiro está na lista e na legenda. */
function abreviar(nome: string, max: number) {
  return nome.length > max ? `${nome.slice(0, max - 1).trimEnd()}…` : nome;
}

const semMovimento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * O panóptico invertido da marca: a torre (o governo) no centro e, em volta, um olho por
 * apoiador, com a pupila voltada para ela e um cone de visão que a ilumina. Quanto mais olhos,
 * mais clara a torre. No computador o nome vai escrito ao longo do olhar; no celular, onde não
 * cabe legível, só os olhos aparecem e os nomes ficam na lista logo abaixo. Com menos de 12
 * nomes, olhos fechados completam o anel. Os olhos piscam de vez em quando (o intervalo cresce
 * com o número de nomes, para o desenho não piscar demais) e ao serem destacados. O desenho é
 * decorativo (aria-hidden); a lista de botões é o caminho por teclado e leitor de tela.
 */
export function OlhosApoiadores({ apoiadores }: { apoiadores: Apoiador[] }) {
  const [ativo, setAtivo] = useState<number | null>(null);
  const [anuncio, setAnuncio] = useState("");
  // Animações da piscada (pálpebra e pupila) de cada olho, disparadas por beginElement().
  const piscadas = useRef<(SVGAnimationElement | null)[][]>([]);
  const n = apoiadores.length;
  const total = Math.max(12, n);
  const dois = total > 24;
  const fonte = n > 40 ? 11 : 13.5;
  const maxCaracteres = n > 40 ? 28 : 24;
  const atual = ativo !== null ? apoiadores[ativo] : null;
  const raioOlho = (i: number) => (dois && i % 2 === 1 ? R_OLHO_CURTO : R_OLHO);
  const meioCone = Math.max(8, Math.min(20, 300 / total)); // meia-abertura do cone na torre
  const luz = Math.min(0.12 + n * 0.022, 0.75); // a torre acende conforme o número de olhares

  const piscar = (k: number) => piscadas.current[k]?.forEach((a) => a?.beginElement());

  // Cada olho pisca a cada 6 a 15 s até 8 nomes; acima disso o intervalo cresce na mesma
  // proporção, e o desenho inteiro fica perto de uma piscada a cada 1,3 s.
  useEffect(() => {
    if (semMovimento()) return;
    const fator = Math.max(1, n / 8);
    const timers = new Set<ReturnType<typeof setTimeout>>();
    const depois = (ms: number, f: () => void) => {
      const t = setTimeout(() => {
        timers.delete(t);
        f();
      }, ms);
      timers.add(t);
    };
    const agendar = (k: number) =>
      depois((6000 + Math.random() * 9000) * fator, () => {
        piscar(k);
        if (Math.random() < 0.15) depois(320, () => piscar(k));
        agendar(k);
      });
    for (let k = 0; k < n; k++) agendar(k);
    return () => timers.forEach(clearTimeout);
  }, [n]);

  // Piscadinha ao ser destacado (só na troca de destaque, não a cada movimento do mouse).
  useEffect(() => {
    if (ativo !== null && !semMovimento()) piscar(ativo);
  }, [ativo]);

  // Olhos espalhados pelo anel (não vizinhos), começando meio passo depois do alto.
  const acesos = new Map<number, number>(); // posto -> índice do apoiador
  apoiadores.forEach((_, k) => acesos.set(Math.floor((k * total) / n), k));

  // Tamanho do desenho: no computador, até o fim do maior nome escrito; no celular, só até os olhos.
  const alcance = apoiadores.map((a, k) => {
    const i = Math.floor((k * total) / n);
    const dist = R_OLHO + 18 + abreviar(a.nome, maxCaracteres).length * fonte * 0.56;
    const ang = (((i + 0.5) / total) * 360 - 90) * (Math.PI / 180);
    return Math.max(Math.abs(dist * Math.cos(ang)), Math.abs(dist * Math.sin(ang)));
  });
  const R = Math.min(318, Math.ceil(Math.max(156, ...alcance) + 14)); // metade do lado, no computador
  const Rm = 156; // metade do lado, no celular
  const estilo = {
    "--larg": `${r2((R / Rm) * 100)}%`,
    "--desloc": `${r2(((R - Rm) / (2 * Rm)) * 100)}%`,
  } as React.CSSProperties;

  return (
    <div className="flex flex-col gap-4">
      {/* No celular, sem os nomes, o desenho é recortado em volta dos olhos para não ficarem pequenos. */}
      <div className="mx-auto aspect-square w-full max-w-[34rem] overflow-hidden" style={estilo}>
        <svg
          viewBox={`${C - R} ${C - R} ${2 * R} ${2 * R}`}
          aria-hidden
          className="mt-[calc(var(--desloc)*-1)] ml-[calc(var(--desloc)*-1)] block h-auto w-[var(--larg)] max-w-none text-foreground md:m-0 md:w-full"
        >
          {/* Cones de visão por baixo de tudo: se sobrepõem na torre. */}
          {apoiadores.map((_, k) => {
            const i = Math.floor((k * total) / n);
            const theta = ((i + 0.5) / total) * 360;
            const ro = raioOlho(i);
            return (
              <polygon
                key={k}
                points={`${ro - 8},-2.5 ${ro - 8},2.5 ${R_TORRE - 4},${r2(meioCone)} ${R_TORRE - 4},${r2(-meioCone)}`}
                transform={`translate(${C} ${C}) rotate(${r2(theta - 90)})`}
                className="olho-cone fill-bronze transition-opacity duration-300 motion-reduce:transition-none"
                opacity={ativo === k ? 0.4 : ativo !== null ? 0.05 : 0.1}
                style={{ "--atraso": `${-k * 0.7}s` } as React.CSSProperties}
              />
            );
          })}
          <circle cx={C} cy={C} r={R_TORRE + 22} className="olho-torre fill-bronze" opacity={r2(luz * 0.35)} />
          <circle cx={C} cy={C} r={R_TORRE} className="fill-bronze" opacity={r2(luz)} />
          <circle cx={C} cy={C} r={R_TORRE} className="fill-none stroke-bronze" strokeWidth="3" />
          {Array.from({ length: total }, (_, i) => {
            const theta = ((i + 0.5) / total) * 360; // 0 = para cima, sentido horário
            const k = acesos.get(i);
            const ro = raioOlho(i);
            return (
              <g key={i} transform={`translate(${C} ${C}) rotate(${r2(theta - 90)})`}>
                {k === undefined ? (
                  <path d={`M${ro},-8 Q${ro - 4},0 ${ro},8`} strokeLinecap="round" strokeWidth="2" className="fill-none stroke-border" />
                ) : (
                  <Olho
                    nome={abreviar(apoiadores[k].nome, maxCaracteres)}
                    raio={ro}
                    raioNome={R_OLHO + 18}
                    virado={theta > 180}
                    fonte={fonte}
                    destaque={ativo === k}
                    algumAtivo={ativo !== null}
                    atraso={k * 60}
                    piscada={(el, j) => {
                      (piscadas.current[k] ??= [])[j] = el as SVGAnimationElement | null;
                    }}
                    aoEntrar={() => setAtivo(k)}
                    aoSair={() => setAtivo((v) => (v === k ? null : v))}
                  />
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <p className="min-h-6 text-center text-sm text-muted-foreground">
        {atual ? (
          <>
            <span className="font-semibold text-foreground">{atual.nome}</span>
            {atual.desde && <> · apoia desde {atual.desde}</>}
          </>
        ) : (
          "Passe o mouse, toque ou clique num olho ou num nome."
        )}
      </p>

      <p role="status" className="sr-only">
        {anuncio}
      </p>

      <ul className="grid gap-x-8 sm:grid-cols-2 lg:grid-cols-3">
        {apoiadores.map((a, i) => (
          <li key={a.nome} className="border-t border-border">
            <button
              type="button"
              onClick={() => {
                setAtivo(i);
                setAnuncio(a.desde ? `${a.nome}, apoia desde ${a.desde}` : a.nome);
              }}
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

function Olho({
  nome,
  raio,
  raioNome,
  virado,
  fonte,
  destaque,
  algumAtivo,
  atraso,
  piscada,
  aoEntrar,
  aoSair,
}: {
  nome: string;
  raio: number;
  raioNome: number;
  virado: boolean;
  fonte: number;
  destaque: boolean;
  algumAtivo: boolean;
  atraso: number;
  piscada: (el: SVGElement | null, j: number) => void;
  aoEntrar: () => void;
  aoSair: () => void;
}) {
  // A piscada muda o próprio desenho (pálpebra e pupila) em vez de escalar o grupo, que borra o traço.
  const aberto = `M${raio},-11 Q${raio - 9},0 ${raio},11 Q${raio + 9},0 ${raio},-11 Z`;
  const fechado = `M${raio},-11 Q${raio - 0.6},0 ${raio},11 Q${raio + 0.6},0 ${raio},-11 Z`;
  return (
    <g
      onMouseEnter={aoEntrar}
      onMouseLeave={aoSair}
      onClick={aoEntrar}
      className={`olho-entra cursor-pointer transition-opacity duration-300 motion-reduce:transition-none ${algumAtivo && !destaque ? "opacity-45" : "opacity-100"}`}
      style={{ "--atraso": `${atraso}ms` } as React.CSSProperties}
    >
      {/* Área de toque maior que o olho. */}
      <rect x={R_TORRE + 10} y="-11" width={raio - R_TORRE} height="22" fill="transparent" />
      <path
        d={aberto}
        strokeWidth={destaque ? 3 : 2.2}
        strokeLinejoin="round"
        className="fill-card stroke-bronze"
        style={destaque ? { filter: "drop-shadow(0 0 4px var(--bronze))" } : undefined}
      >
        <animate ref={(el) => piscada(el, 0)} attributeName="d" values={`${aberto};${fechado};${aberto}`} dur="0.22s" begin="indefinite" />
      </path>
      <ellipse cx={raio - 2.5} cy="0" rx="3.2" ry="3.2" className="fill-bronze">
        <animate ref={(el) => piscada(el, 1)} attributeName="rx" values="3.2;0;3.2" dur="0.22s" begin="indefinite" />
        <animate ref={(el) => piscada(el, 2)} attributeName="cx" values={`${raio - 2.5};${raio};${raio - 2.5}`} dur="0.22s" begin="indefinite" />
      </ellipse>
      <text
        x={virado ? -raioNome : raioNome}
        y={r2(fonte * 0.35)}
        textAnchor={virado ? "end" : "start"}
        transform={virado ? "rotate(180)" : undefined}
        fontSize={fonte}
        className={`hidden md:block ${destaque ? "fill-foreground font-semibold" : "fill-muted-foreground"}`}
      >
        {nome}
      </text>
    </g>
  );
}
