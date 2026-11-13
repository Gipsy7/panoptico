"use client";

import { useMemo, useState } from "react";

import { Segmentado } from "@/components/segmentado";
import { FonteRodape } from "@/components/fonte-rodape";
import {
  agrupar,
  cadeirasPorPartido,
  cadeirasPorVoto,
  descricaoCadeiras,
  descricaoVotos,
  layoutCadeiras,
  totalDe,
  type ItemBancada,
} from "@/lib/cadeiras";

const SEM_ITENS: ItemBancada[] = [];
type Fonte = { nome: string; url?: string; atualizadoEm?: string | null };

/**
 * Cadeiras do plenário em semicírculo: uma bolinha por cadeira, um tom só (tokens do tema),
 * agrupadas por partido. Tocar (ou Enter/Espaço) num partido da legenda o destaca; sem
 * `escolhido`, o destaque fica no próprio componente. Com `onEscolher`, o pai também é avisado
 * (na lista de parlamentares, aplica o filtro de partido). Alternância "Hoje | A partir de
 * fev/2027" quando há `depois`.
 *
 * Modo `porVoto`: as bolinhas deixam de ser partidos e passam a ser Sim (cheia), Não (vazada)
 * e outro registro (tracejada), com legenda em texto e o placar.
 */
export function Cadeiras({
  nome,
  hoje = SEM_ITENS,
  depois,
  rotuloHoje = "Hoje",
  rotuloDepois = "A partir de fev/2027",
  fonte,
  fonteDepois,
  escolhido,
  onEscolher,
  porVoto,
  titulo,
  nivelTitulo = 3,
}: {
  nome: string;
  hoje?: ItemBancada[];
  depois?: ItemBancada[] | null;
  rotuloHoje?: string;
  rotuloDepois?: string;
  fonte: Fonte;
  fonteDepois?: Fonte | null;
  /** Partido destacado (controlado). Omitido, o componente guarda o próprio destaque. */
  escolhido?: string | null;
  onEscolher?: (partido: string | null) => void;
  porVoto?: { sim: number; nao: number; outros: number; rotuloOutros?: string };
  titulo?: string;
  /** 2 quando o gráfico abre a página, antes de qualquer h2 (ordem dos títulos). */
  nivelTitulo?: 2 | 3;
}) {
  const Titulo = nivelTitulo === 2 ? "h2" : "h3";
  const [quando, setQuando] = useState<"hoje" | "depois">("hoje");
  const [interno, setInterno] = useState<string | null>(null);
  const destaque = escolhido !== undefined ? escolhido : interno;
  const temDepois = !porVoto && !!depois && depois.length > 0;
  const itens = useMemo(() => agrupar(quando === "depois" && depois ? depois : hoje), [quando, depois, hoje]);
  const total = porVoto ? porVoto.sim + porVoto.nao + porVoto.outros : totalDe(itens);
  const { pontos, altura, raio } = useMemo(() => layoutCadeiras(total), [total]);
  const serie = useMemo<string[]>(
    () => (porVoto ? cadeirasPorVoto(porVoto.sim, porVoto.nao, porVoto.outros) : cadeirasPorPartido(itens)),
    [porVoto, itens],
  );
  const fonteAtual = quando === "depois" && fonteDepois ? fonteDepois : fonte;
  const periodo = quando === "depois" ? rotuloDepois : rotuloHoje;
  const rotuloOutros = porVoto?.rotuloOutros ?? "Outro registro ou sem voto";

  function escolher(partido: string) {
    const novo = destaque === partido ? null : partido;
    if (escolhido === undefined) setInterno(novo);
    onEscolher?.(novo);
  }

  const alt = porVoto
    ? descricaoVotos(nome, porVoto.sim, porVoto.nao, porVoto.outros)
    : `${descricaoCadeiras(nome, itens)} ${temDepois ? `Composição: ${periodo.toLowerCase()}.` : ""}`;

  if (total === 0) {
    return (
      <div className="flex flex-col gap-2">
        {titulo && <Titulo className="font-sans text-lg font-semibold tracking-normal">{titulo}</Titulo>}
        <p className="text-sm text-muted-foreground">Sem dados de cadeiras na fonte.</p>
        <FonteRodape fonte={fonte.nome} url={fonte.url} atualizadoEm={fonte.atualizadoEm} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {titulo && <Titulo className="font-sans text-lg font-semibold tracking-normal">{titulo}</Titulo>}
        {temDepois && (
          <Segmentado
            rotulo="Qual composição mostrar"
            opcoes={[
              { valor: "hoje", rotulo: rotuloHoje },
              { valor: "depois", rotulo: rotuloDepois },
            ]}
            valor={quando}
            aoMudar={setQuando}
          />
        )}
      </div>
      <svg
        role="img"
        aria-label={alt}
        viewBox={`0 0 360 ${altura.toFixed(1)}`}
        className="h-auto w-full max-w-lg"
      >
        {pontos.map((p, i) => {
          const chave = serie[i];
          const cx = p.x.toFixed(1);
          const cy = p.y.toFixed(1);
          if (porVoto) {
            if (chave === "sim") return <circle key={i} cx={cx} cy={cy} r={raio} className="fill-chart-3" />;
            if (chave === "nao")
              return <circle key={i} cx={cx} cy={cy} r={raio * 0.85} className="fill-none stroke-chart-3" strokeWidth={raio * 0.35} />;
            return (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={raio * 0.85}
                className="fill-none stroke-chart-3"
                strokeWidth={raio * 0.3}
                strokeDasharray={`${raio * 0.6} ${raio * 0.5}`}
              />
            );
          }
          const aceso = destaque === chave;
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={raio}
              className={aceso ? "fill-bronze" : destaque ? "fill-chart-3 opacity-30" : "fill-chart-3"}
            />
          );
        })}
        <text x="180" y={(altura - 6).toFixed(1)} textAnchor="middle" className="fill-foreground text-[22px] font-semibold tabular-nums" aria-hidden>
          {total}
        </text>
      </svg>

      {porVoto ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm tabular-nums">
          <li className="flex items-center gap-1.5">
            <svg aria-hidden width="12" height="12" viewBox="0 0 12 12">
              <circle cx="6" cy="6" r="5" className="fill-chart-3" />
            </svg>
            Sim <span className="font-semibold">{porVoto.sim}</span>
          </li>
          <li className="flex items-center gap-1.5">
            <svg aria-hidden width="12" height="12" viewBox="0 0 12 12">
              <circle cx="6" cy="6" r="4.2" className="fill-none stroke-chart-3" strokeWidth="1.8" />
            </svg>
            Não <span className="font-semibold">{porVoto.nao}</span>
          </li>
          <li className="flex items-center gap-1.5">
            <svg aria-hidden width="12" height="12" viewBox="0 0 12 12">
              <circle cx="6" cy="6" r="4.2" className="fill-none stroke-chart-3" strokeWidth="1.6" strokeDasharray="2.2 1.8" />
            </svg>
            {rotuloOutros} <span className="font-semibold">{porVoto.outros}</span>
          </li>
        </ul>
      ) : (
        <ul className="flex flex-wrap gap-x-2 gap-y-0.5 text-sm tabular-nums">
          {itens.map((i) => (
            <li key={i.partido}>
              <button
                type="button"
                aria-pressed={destaque === i.partido}
                onClick={() => escolher(i.partido)}
                className="min-h-11 rounded-md px-1.5 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze aria-pressed:bg-accent aria-pressed:font-semibold"
              >
                {i.partido} <span className="font-semibold">{i.n}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <p role="status" className="sr-only">
        {porVoto ? "" : destaque ? `Partido em destaque: ${destaque}.` : `Mostrando ${periodo.toLowerCase()}.`}
      </p>
      <FonteRodape fonte={fonteAtual.nome} url={fonteAtual.url} atualizadoEm={fonteAtual.atualizadoEm} />
    </div>
  );
}
