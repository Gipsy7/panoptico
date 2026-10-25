"use client";

/**
 * "De Brasília até a sua rua": desenho com os prédios de quem representa o cidadão (país, estado
 * e cidade). Tocar num prédio abre ao lado (computador) ou embaixo (celular) o painel dele: o que
 * faz, quantos são e até 6 rostos. A lista completa continua na gaveta `#ver-<destino>` do
 * <AbasDetalhe>; este componente só aponta para ela. Recebe dados simples, já montados na página.
 *
 * Uma mão "TOQUE" passeia pelos prédios até o primeiro toque; com prefers-reduced-motion ela
 * fica parada no primeiro prédio do roteiro.
 */
import Link from "next/link";
import { type KeyboardEvent, type ReactNode, useEffect, useId, useRef, useState } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { MaoToque, useMovimentoReduzido } from "@/components/mao-toque";
import { type PredioId, larguraFaixa, medidasDoDesenho, predioInicial, roteiroDaMao } from "@/lib/predios";

export type PessoaPredio = {
  chave: string;
  nome: string;
  partido: string | null;
  /** Linha menor abaixo do nome (cargo, eleição, vice). */
  detalhe: string | null;
  foto: string | null;
  href: string | null;
};

export type PredioDados = {
  id: PredioId;
  /** "País · Brasília". */
  nivel: string;
  nome: string;
  /** Nome oficial, em letra menor. */
  oficial: string;
  /** O que faz, no dia a dia. */
  faz: string;
  fazOficial: string;
  /** Legenda curta embaixo do prédio e a contagem ("3 senadores"). */
  rotulo: string;
  sub: string;
  total: number;
  tituloPessoas: string;
  /** Até ~6 pessoas; o resto fica na lista completa. */
  pessoas: PessoaPredio[];
  /** Seção da gaveta (`#ver-<destino>`); sem ela o botão não aparece. */
  destino: string | null;
  aviso: string | null;
  fonte: { nome: string; url?: string; atualizadoEm?: string | null } | null;
  extra: { href: string; rotulo: string } | null;
};

const F1 = (sel: boolean) =>
  sel
    ? "fill-chart-2 stroke-bronze-texto [stroke-width:2]"
    : "fill-card stroke-foreground group-hover/p:fill-accent";
const F2 = (sel: boolean) =>
  sel
    ? "fill-chart-2 stroke-bronze-texto [stroke-width:2]"
    : "fill-muted stroke-foreground group-hover/p:fill-accent";
const TR = "fill-none stroke-foreground";
const BASE = "fill-muted stroke-foreground";

function Colunas({ x0, n, passo, y, alt, larg, cls }: { x0: number; n: number; passo: number; y: number; alt: number; larg: number; cls: string }) {
  return (
    <>
      {Array.from({ length: n }, (_, i) => (
        <rect key={i} className={cls} strokeWidth={1.5} x={x0 + i * passo} y={y} width={larg} height={alt} />
      ))}
    </>
  );
}

type Corpo = (f1: string, f2: string) => ReactNode;

const CORPOS: Record<PredioId, Corpo> = {
  planalto: (f1, f2) => (
    <>
      <rect className={f2} strokeWidth={1.5} x={14} y={68} width={158} height={10} />
      <Colunas x0={24} n={9} passo={16.5} y={78} alt={46} larg={7} cls={f1} />
      <rect className={f2} strokeWidth={1.5} x={18} y={124} width={150} height={12} />
      <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M18 136 L18 144 M168 136 L168 144" />
      <path className={f1} strokeWidth={1.5} d="M100 136 L130 150 L160 150 L160 136 Z" transform="translate(-6 0)" />
    </>
  ),
  senado: (f1) => (
    <>
      <path className={f1} strokeWidth={1.5} d="M188 128 A33 33 0 0 1 254 128 Z" />
      <rect className={f1} strokeWidth={1.5} x={192} y={128} width={58} height={6} />
      <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M221 95 V86" />
      <circle className={f1} strokeWidth={1.5} cx={221} cy={83} r={3} />
    </>
  ),
  camara: (f1) => (
    <>
      <path className={f1} strokeWidth={1.5} d="M274 96 A33 33 0 0 0 340 96 Z" />
      <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M307 130 V140" />
      <rect className={f1} strokeWidth={1.5} x={272} y={92} width={70} height={5} />
    </>
  ),
  governo: (f1, f2) => (
    <>
      <path className={f2} strokeWidth={1.5} d="M14 290 L93 266 L172 290 Z" />
      <Colunas x0={26} n={8} passo={18} y={292} alt={52} larg={8} cls={f1} />
      <rect className={f2} strokeWidth={1.5} x={14} y={344} width={158} height={14} />
      <circle className={f1} strokeWidth={1.5} cx={93} cy={282} r={5} />
    </>
  ),
  assembleia: (f1, f2) => (
    <>
      <path className={f1} strokeWidth={1.5} d="M240 300 A28 28 0 0 1 296 300 Z" />
      <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M268 272 V262" />
      <rect className={f2} strokeWidth={1.5} x={236} y={300} width={64} height={10} />
      <Colunas x0={196} n={7} passo={20} y={312} alt={34} larg={8} cls={f1} />
      <rect className={f2} strokeWidth={1.5} x={190} y={346} width={154} height={12} />
    </>
  ),
  prefeitura: (f1, f2) => (
    <>
      <rect className={f1} strokeWidth={1.5} x={14} y={528} width={158} height={52} />
      <path className={f2} strokeWidth={1.5} d="M14 528 L93 508 L172 528 Z" />
      <rect className={f2} strokeWidth={1.5} x={76} y={478} width={34} height={34} />
      <circle className={f1} strokeWidth={1.5} cx={93} cy={495} r={9} />
      <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M93 489 V495 L98 497" />
      <path className={f2} strokeWidth={1.5} d="M72 478 L93 464 L114 478 Z" />
      <Colunas x0={28} n={5} passo={30} y={540} alt={22} larg={14} cls={f2} />
      <rect className={f2} strokeWidth={1.5} x={78} y={558} width={30} height={22} />
    </>
  ),
  camaramun: (f1, f2) => (
    <>
      <path className={f2} strokeWidth={1.5} d="M190 516 L267 494 L344 516 Z" />
      <Colunas x0={204} n={5} passo={28} y={518} alt={40} larg={9} cls={f1} />
      <rect className={f2} strokeWidth={1.5} x={196} y={558} width={142} height={8} />
      <rect className={f2} strokeWidth={1.5} x={190} y={566} width={154} height={10} />
    </>
  ),
};

/** Área que recebe o toque (x, y, largura, altura) e onde ficam as legendas. */
const AREAS: Record<PredioId, { hit: [number, number, number, number]; cx: number; ancora: "start" | "middle" }> = {
  planalto: { hit: [10, 52, 166, 104], cx: 14, ancora: "start" },
  senado: { hit: [186, 80, 72, 70], cx: 221, ancora: "middle" },
  camara: { hit: [270, 80, 74, 70], cx: 307, ancora: "middle" },
  governo: { hit: [10, 258, 166, 104], cx: 14, ancora: "start" },
  assembleia: { hit: [186, 252, 162, 112], cx: 190, ancora: "start" },
  prefeitura: { hit: [10, 458, 166, 128], cx: 14, ancora: "start" },
  camaramun: { hit: [186, 484, 162, 100], cx: 190, ancora: "start" },
};

/** Centro de cada prédio, onde a mão pousa. */
const CENTROS: Record<PredioId, [number, number]> = {
  planalto: [93, 104],
  senado: [222, 115],
  camara: [307, 115],
  governo: [93, 310],
  assembleia: [267, 308],
  prefeitura: [93, 522],
  camaramun: [267, 534],
};

function Faixa({ y, texto }: { y: number; texto: string }) {
  const larg = larguraFaixa(texto);
  return (
    <>
      <rect className="fill-background stroke-border" x={180 - larg / 2} y={y} width={larg} height={26} rx={13} />
      <text className="fill-bronze-texto text-[11px] font-semibold tracking-[0.08em]" x={180} y={y + 17} textAnchor="middle">
        {texto}
      </text>
    </>
  );
}

export function PrediosRepresentantes({
  predios,
  faixaBrasil = "BRASIL · BRASÍLIA",
  faixaEstado,
  faixaCidade,
  voce,
}: {
  predios: PredioDados[];
  faixaBrasil?: string;
  faixaEstado: string;
  /** Nulo quando a busca foi só por estado (ou no DF): o desenho termina no estado. */
  faixaCidade: string | null;
  /** "Você, em Gaspar". */
  voce: string;
}) {
  const base = useId();
  const ids = predios.map((p) => p.id);
  const porId = new Map(predios.map((p) => [p.id, p]));
  const roteiro = roteiroDaMao(ids);
  const [escolhido, setEscolhido] = useState<PredioId>(() => predioInicial(ids));
  const [tocou, setTocou] = useState(false);
  const [passo, setPasso] = useState(0);
  const reduzido = useMovimentoReduzido();
  const painel = useRef<HTMLElement>(null);
  const desenho = useRef<HTMLDivElement>(null);
  const med = medidasDoDesenho(faixaCidade != null);

  // A mão troca de prédio a cada 2,6 s até o primeiro toque; com movimento reduzido, fica parada.
  useEffect(() => {
    if (tocou || reduzido || roteiro.length < 2) return;
    const t = setInterval(() => setPasso((i) => (i + 1) % roteiro.length), 2600);
    return () => clearInterval(t);
  }, [tocou, reduzido, roteiro.length]);

  const daVez = roteiro[passo % Math.max(roteiro.length, 1)];
  const [mx, my] = CENTROS[daVez] ?? [180, 100];

  function escolher(id: PredioId) {
    setTocou(true);
    setEscolhido(id);
    if (window.matchMedia("(max-width: 899px)").matches) {
      painel.current?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "start" });
      painel.current?.focus({ preventScroll: true });
    }
  }
  function aoTeclar(e: KeyboardEvent, id: PredioId) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      escolher(id);
    }
  }
  function voltarAoDesenho() {
    desenho.current?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "start" });
  }

  const sel = porId.get(escolhido) ?? predios[0];
  if (!sel) return null;

  return (
    <div className="grid min-w-0 gap-5 min-[900px]:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] min-[900px]:items-start min-[900px]:gap-10">
      <div
        ref={desenho}
        className="mx-auto w-full max-w-[30rem] scroll-mt-[calc(var(--altura-cabecalho)+0.75rem)] min-[900px]:sticky min-[900px]:top-[calc(var(--altura-cabecalho)+1rem)]"
      >
        <svg
          viewBox={`0 0 360 ${med.altura}`}
          role="group"
          aria-label={`Desenho com ${predios.length} prédios, de Brasília até ${voce.replace(/^Você, em /, "")}. Cada prédio é um botão.`}
          className="block h-auto w-full min-[900px]:max-h-[calc(100vh-var(--altura-cabecalho)-6rem)]"
        >
          <path d={med.caminho} className="fill-none stroke-bronze" strokeWidth={3} strokeDasharray="2 9" strokeLinecap="round" />
          <Faixa y={10} texto={faixaBrasil} />
          <rect className={BASE} strokeWidth={1.5} x={184} y={134} width={160} height={12} />
          <rect className={BASE} strokeWidth={1.5} x={252} y={60} width={9} height={74} />
          <rect className={BASE} strokeWidth={1.5} x={266} y={60} width={9} height={74} />
          <path className={TR} strokeWidth={1.5} strokeLinecap="round" d="M256 52 V60 M270 52 V60" />
          <Faixa y={222} texto={faixaEstado} />
          {faixaCidade && <Faixa y={430} texto={faixaCidade} />}

          {predios.map((p) => {
            const eSel = p.id === escolhido;
            const convite = !tocou && p.id === daVez;
            const a = AREAS[p.id];
            const [hx, hy, hw, hh] = a.hit;
            return (
              <g
                key={p.id}
                role="button"
                tabIndex={0}
                aria-pressed={eSel}
                aria-labelledby={`${base}-${p.id}-r ${base}-${p.id}-s`}
                className="group/p cursor-pointer outline-none"
                onClick={() => escolher(p.id)}
                onKeyDown={(e) => aoTeclar(e, p.id)}
              >
                <rect
                  x={hx}
                  y={hy}
                  width={hw}
                  height={hh}
                  rx={4}
                  strokeWidth={2}
                  strokeDasharray={convite ? "6 5" : undefined}
                  className={`fill-transparent [pointer-events:all] group-focus-visible/p:stroke-bronze group-focus-visible/p:[stroke-dasharray:5_4] ${
                    eSel || convite ? "stroke-bronze" : "stroke-transparent"
                  }`}
                >
                  {convite && !reduzido && (
                    <animate attributeName="stroke-dashoffset" from="0" to="-22" dur="1s" repeatCount="indefinite" />
                  )}
                </rect>
                {CORPOS[p.id](F1(eSel), F2(eSel))}
                <text
                  id={`${base}-${p.id}-r`}
                  className={`fill-foreground text-[15px] font-semibold ${eSel ? "underline decoration-bronze underline-offset-[3px]" : ""}`}
                  x={a.cx}
                  y={hy + hh + 20}
                  textAnchor={a.ancora}
                >
                  {/* Espaço no fim: o texto do grupo vira "Senado 3 senadores", igual ao nome acessível (WCAG 2.5.3). */}
                  {p.rotulo}{" "}
                </text>
                <text id={`${base}-${p.id}-s`} className="fill-muted-foreground text-[13px]" x={a.cx} y={hy + hh + 38} textAnchor={a.ancora}>
                  {p.sub}
                </text>
              </g>
            );
          })}

          <circle className="fill-none stroke-bronze" strokeWidth={2} cx={180} cy={med.yVoce} r={20} />
          <circle className="fill-bronze stroke-background" strokeWidth={3} cx={180} cy={med.yVoce} r={10} />
          <text className="fill-foreground text-[15px] font-semibold" x={180} y={med.yVoce + 44} textAnchor="middle">
            {voce}
          </text>

          <MaoToque x={mx} y={my} oculta={tocou} reduzido={reduzido} etiquetaEsquerda={mx > 240} />
        </svg>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          {tocou ? "Toque em outro prédio para comparar." : "Toque num prédio para ver quem trabalha lá."}
        </p>
      </div>

      <aside
        ref={painel}
        id="painel-predio"
        tabIndex={-1}
        aria-live="polite"
        aria-label="Quem trabalha no prédio escolhido"
        className="min-w-0 scroll-mt-[calc(var(--altura-cabecalho)+0.75rem)] rounded-[var(--radius)] border border-border bg-card p-5 focus:outline-none focus-visible:outline-2 focus-visible:outline-bronze"
      >
        <p className="sobretitulo">{sel.nivel}</p>
        <h2 className="mt-1 text-[1.6rem] leading-tight">{sel.nome}</h2>
        <p className="text-xs text-muted-foreground">{sel.oficial}</p>
        <div className="my-4 border-l-[3px] border-bronze pl-3">
          <p className="text-lg leading-snug">{sel.faz}</p>
          <p className="text-xs text-muted-foreground">Termo oficial: {sel.fazOficial}</p>
        </div>

        <h3 className="mt-5 text-base font-semibold">{sel.tituloPessoas}</h3>
        {sel.aviso && <p className="mt-2 border-l-[3px] border-bronze bg-background px-3 py-2 text-sm">{sel.aviso}</p>}
        {sel.pessoas.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Ainda não há dados carregados para este prédio.</p>
        ) : (
          <ul className="mt-1">
            {sel.pessoas.map((p) => (
              <li key={p.chave} className="border-t border-border first:border-t-0">
                <LinhaPessoa pessoa={p} />
              </li>
            ))}
          </ul>
        )}
        {sel.total > sel.pessoas.length && (
          <p className="mt-1 text-sm text-muted-foreground">
            Mostrando {sel.pessoas.length} de {sel.total.toLocaleString("pt-BR")}.
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {sel.destino && (
            <a href={`#ver-${sel.destino}`} className="botao-linha">
              Ver a lista com os números
            </a>
          )}
          {sel.extra && (
            <a href={sel.extra.href} className="botao-linha">
              {sel.extra.rotulo}
            </a>
          )}
        </div>
        {sel.fonte && (
          <div className="mt-4 border-t border-border pt-2">
            <FonteRodape fonte={sel.fonte.nome} url={sel.fonte.url} atualizadoEm={sel.fonte.atualizadoEm} />
          </div>
        )}
        <button type="button" onClick={voltarAoDesenho} className="botao-linha mt-4 min-[900px]:hidden">
          Voltar ao desenho
        </button>
      </aside>
    </div>
  );
}

function LinhaPessoa({ pessoa }: { pessoa: PessoaPredio }) {
  const corpo = (
    <>
      <Retrato nome={pessoa.nome} foto={pessoa.foto} />
      <span className="min-w-0 flex-1">
        <span className="block font-semibold [overflow-wrap:anywhere]">
          {pessoa.nome}
          {pessoa.partido && <> <span className="pilula">{pessoa.partido}</span></>}
        </span>
        {pessoa.detalhe && <span className="block text-sm text-muted-foreground">{pessoa.detalhe}</span>}
      </span>
    </>
  );
  const classes =
    "flex min-h-11 items-start gap-3 py-2.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze";
  return pessoa.href ? (
    <Link href={pessoa.href} className={`${classes} hover:bg-accent/50`}>
      {corpo}
    </Link>
  ) : (
    <div className={classes}>{corpo}</div>
  );
}

function Retrato({ nome, foto }: { nome: string; foto: string | null }) {
  const larg = 36;
  const alt = 48;
  if (foto) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- fotos já reduzidas, da API e da Câmara/Senado
      <img
        src={foto}
        alt={`Foto de ${nome}`}
        width={larg}
        height={alt}
        loading="lazy"
        className="shrink-0 rounded-[2px] bg-muted object-cover"
        style={{ width: larg, height: alt }}
      />
    );
  }
  const partes = nome.split(/\s+/).filter((w) => w && !["da", "de", "do", "dos", "das", "e"].includes(w.toLowerCase()));
  const iniciais = ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes.at(-1)![0] : "")).toUpperCase();
  return (
    <span
      aria-hidden
      style={{ width: larg, height: alt }}
      className="flex shrink-0 items-center justify-center rounded-[2px] bg-muted font-heading text-sm text-foreground"
    >
      {iniciais}
    </span>
  );
}
