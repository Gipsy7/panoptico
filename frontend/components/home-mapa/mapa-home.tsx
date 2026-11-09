"use client";

// Mapa da home como ferramenta de exploração (protótipo A): assuntos e camadas (o dinheiro da
// União e os indicadores dos estados), régua de anos, "comparar com" (pontos dos 27 estados
// ligados ao mapa) e a lista do maior para o menor, com a ordem escrita. Título, legenda, ficha e
// fonte mudam junto com a camada. No computador o resumo segue o mouse e o clique abre o estado;
// no celular o 1º toque mostra o resumo e o 2º abre a página do estado.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { MaoToque, useMovimentoReduzido } from "@/components/mao-toque";
import { MapaBrasil } from "@/components/mapa/mapa-brasil";
import estilos from "@/components/mapa/mapa-brasil.module.css";
import { Segmentado } from "@/components/segmentado";
import type { IndicadoresUfs } from "@/lib/api";
import {
  anoDaCamada,
  type Camada,
  correlacao,
  frasePadrao,
  montarCamadas,
  ordenarDoMaior,
  type UfDinheiro,
} from "@/lib/camadas-mapa";
import { classe, quantis, type ClasseMapa } from "@/lib/mapa";

export type UfDoMapa = UfDinheiro;

/** Primeira letra minúscula, menos em sigla ("IDEB", "PIB"). */
const minuscula = (t: string) => (t.length > 1 && t[1] === t[1].toUpperCase() && /\p{L}/u.test(t[1]) ? t : t[0].toLowerCase() + t.slice(1));

// Estados por onde a mão passeia: grandes e espalhados, o primeiro bem visível no celular.
const ROTEIRO_MAO = ["PA", "BA", "AM", "MG", "MT", "RS"];

type Pergunta = { texto: string; camada: string; comparar?: string; ano?: "primeiro" };
const PERGUNTAS: Pergunta[] = [
  { texto: "Como os homicídios mudaram ano a ano?", camada: "homicidios", ano: "primeiro" },
  { texto: "Quem gasta mais com segurança tem menos homicídios?", camada: "gasto_seguranca", comparar: "homicidios" },
  { texto: "Estados com PIB maior têm IDEB maior?", camada: "pib", comparar: "ideb" },
];

interface PontoMao {
  uf: string;
  x: number;
  y: number;
  largura: number;
}

function Dispersao({
  ufs,
  x,
  y,
  anoX,
  anoY,
  realce,
  aoRealcar,
}: {
  ufs: UfDinheiro[];
  x: Camada;
  y: Camada;
  anoX: number | null;
  anoY: number | null;
  realce: string | null;
  aoRealcar: (uf: string | null) => void;
}) {
  const pts = ufs
    .map((u) => ({ uf: u.uf, nome: u.nome, vx: x.valor(u.uf, anoX), vy: y.valor(u.uf, anoY) }))
    .filter((p): p is { uf: string; nome: string; vx: number; vy: number } => p.vx != null && p.vy != null);
  // Comparação só com dado suficiente: ao menos 20 dos 27 estados com os dois números.
  if (pts.length < 20)
    return (
      <p className="text-sm text-muted-foreground">
        Só {pts.length} dos 27 estados têm os dois números; são poucos para comparar.
      </p>
    );
  const xs = pts.map((p) => p.vx);
  const ys = pts.map((p) => p.vy);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  // 5% de margem dentro da área: o maior e o menor não encostam na borda.
  const px = (v: number) => (x1 === x0 ? 50 : 5 + ((v - x0) / (x1 - x0)) * 90);
  const py = (v: number) => (y1 === y0 ? 50 : 95 - ((v - y0) / (y1 - y0)) * 90);
  const r = correlacao(xs, ys);
  const mediana = (v: number[]) => {
    const o = [...v].sort((a, b) => a - b);
    return o.length % 2 ? o[(o.length - 1) / 2] : (o[o.length / 2 - 1] + o[o.length / 2]) / 2;
  };
  const [mdx, mdy] = [mediana(xs), mediana(ys)];
  const ativo = pts.find((p) => p.uf === realce);
  const quando = (c: Camada, a: number | null) => (a ? ` (${a})` : "");
  return (
    <figure className="m-0 flex flex-col gap-2 border border-t-4 border-border bg-card p-3" style={{ borderTopColor: "var(--tema-votos)" }}>
      <figcaption className="text-sm">
        <span className="block text-xs font-semibold tracking-wider uppercase" style={{ color: "var(--tema-votos)" }}>
          Os 27 estados, um ponto cada
        </span>
        <b>{x.rotulo}</b>
        {quando(x, anoX)} e <b>{minuscula(y.rotulo)}</b>
        {quando(y, anoY)}: {frasePadrao(r)}.
      </figcaption>
      <div className="grid grid-cols-[auto_1fr] gap-x-2">
        <div className="flex flex-col justify-between text-right text-xs text-muted-foreground tabular-nums">
          <span>{y.formatar(y1)}</span>
          <span>{y.formatar(y0)}</span>
        </div>
        <div className="relative aspect-[4/3] border-b border-l border-border">
          {/* Medianas: metade dos estados de cada lado de cada linha tracejada. */}
          <span aria-hidden className="absolute inset-y-0 border-l border-dashed border-muted-foreground/50" style={{ left: `${px(mdx)}%` }} />
          <span aria-hidden className="absolute inset-x-0 border-t border-dashed border-muted-foreground/50" style={{ top: `${py(mdy)}%` }} />
          <span aria-hidden className="absolute top-0.5 text-[0.65rem] text-muted-foreground" style={{ left: `calc(${px(mdx)}% + 3px)` }}>
            metade ← → metade
          </span>
          {pts.map((p) => {
            const ativo = p.uf === realce;
            return (
              <button
                key={p.uf}
                type="button"
                aria-label={`${p.nome}: ${x.formatar(p.vx)}; ${y.formatar(p.vy)}`}
                title={`${p.nome}: ${x.formatar(p.vx)} · ${y.formatar(p.vy)}`}
                onMouseEnter={() => aoRealcar(p.uf)}
                onMouseLeave={() => aoRealcar(null)}
                onFocus={() => aoRealcar(p.uf)}
                onClick={() => aoRealcar(p.uf)}
                className="absolute flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center"
                style={{ left: `${px(p.vx)}%`, top: `${py(p.vy)}%`, zIndex: ativo ? 2 : 1 }}
              >
                <span
                  aria-hidden
                  className="block rounded-full ring-2 ring-[var(--background)]"
                  style={{ width: ativo ? 14 : 9, height: ativo ? 14 : 9, background: ativo ? "var(--bronze)" : "var(--foreground)" }}
                />
                {ativo && <span className="absolute left-5 text-xs font-semibold whitespace-nowrap">{p.uf}</span>}
              </button>
            );
          })}
        </div>
        <span />
        <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
          <span>{x.formatar(x0)}</span>
          <span>{x.rotulo} →</span>
          <span>{x.formatar(x1)}</span>
        </div>
      </div>
      <p className="min-h-10 text-sm" aria-live="polite">
        {ativo ? (
          <>
            <b>{ativo.nome}</b>: {minuscula(x.rotulo)} {x.formatar(ativo.vx)} ({ativo.vx >= mdx ? "acima" : "abaixo"} da metade
            dos estados); {minuscula(y.rotulo)} {y.formatar(ativo.vy)} ({ativo.vy >= mdy ? "acima" : "abaixo"} da metade).
          </>
        ) : (
          <span className="text-muted-foreground">
            Toque num ponto ou num estado do mapa. Cada linha tracejada marca o meio: metade dos estados fica de cada lado.
          </span>
        )}
      </p>
      <p className="text-xs text-muted-foreground">
        Andar junto não prova que um causa o outro: renda, tamanho, história e quem presta o serviço pesam nos dois.
        {anoX !== anoY && anoX && anoY ? " Os anos dos dois números são diferentes." : ""}
      </p>
    </figure>
  );
}

export function MapaHome({
  ufs,
  fonteObras = null,
  indicadores = null,
  anoDinheiro,
  fonteDinheiro,
}: {
  ufs: UfDoMapa[];
  fonteObras?: string | null;
  indicadores?: IndicadoresUfs | null;
  anoDinheiro: number;
  fonteDinheiro: string;
}) {
  const router = useRouter();
  const NOMES = useMemo(() => Object.fromEntries(ufs.map((u) => [u.uf, u.nome])) as Record<string, string>, [ufs]);
  const camadas = useMemo(
    () => montarCamadas(ufs, indicadores, anoDinheiro, fonteDinheiro, fonteObras),
    [ufs, indicadores, anoDinheiro, fonteDinheiro, fonteObras],
  );
  const grupos = [...new Set(camadas.map((c) => c.grupo))];
  const [camadaId, setCamadaId] = useState(camadas.find((c) => c.id === "homicidios")?.id ?? camadas[0]?.id ?? "retorno");
  const [anoEscolhido, setAnoEscolhido] = useState<number | null>(null);
  const [cmpId, setCmpId] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const [realce, setRealce] = useState<string | null>(null);
  const [aberto, setAberto] = useState<"numero" | "comparar" | "lista" | null>(null);
  const camada = camadas.find((c) => c.id === camadaId) ?? camadas[0];
  const cmp = camadas.find((c) => c.id === cmpId && c.id !== camada.id) ?? null;
  const ano = anoDaCamada(camada, anoEscolhido);
  const anoCmp = cmp ? anoDaCamada(cmp, anoEscolhido) : null;
  const cortes = useMemo(() => quantis(ufs.map((u) => camada.valor(u.uf, ano))), [ufs, camada, ano]);
  const caixa = useRef<HTMLDivElement>(null);
  const [pontos, setPontos] = useState<PontoMao[]>([]);
  const [tocou, setTocou] = useState(false);
  const [passo, setPasso] = useState(0);
  const reduzido = useMovimentoReduzido();
  const foco = realce ?? sel;

  const escolherCamada = (id: string) => {
    setCamadaId(id);
    setAnoEscolhido(null);
    if (id === cmpId) setCmpId("");
  };

  // Centros dos estados medidos na tela depois de montar (sem JS não há mão, então não há salto).
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    const medir = () => {
      const base = el.getBoundingClientRect();
      const l: PontoMao[] = [];
      for (const uf of ROTEIRO_MAO) {
        const p = el.querySelector(`path[data-id="${uf}"]`);
        if (!p) continue;
        const r = p.getBoundingClientRect();
        if (r.width === 0) continue;
        l.push({ uf, x: r.left - base.left + r.width / 2, y: r.top - base.top + r.height / 2, largura: base.width });
      }
      setPontos(l);
    };
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    const t = setTimeout(medir, 600); // malha carrega depois
    return () => {
      ro.disconnect();
      clearTimeout(t);
    };
  }, []);

  useEffect(() => {
    if (tocou || reduzido || pontos.length < 2) return;
    // Passeia 3 voltas pelo roteiro e para (WCAG 2.2.2): a mão fica parada no último estado.
    const limite = 3 * pontos.length - 1;
    const t = setInterval(() => setPasso((i) => (i >= limite ? (clearInterval(t), i) : i + 1)), 2600);
    return () => clearInterval(t);
  }, [tocou, reduzido, pontos.length]);

  // Estado em foco (ponto do gráfico ou toque) com o contorno reforçado no mapa.
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    el.querySelectorAll<SVGPathElement>("path[data-realce]").forEach((p) => {
      p.removeAttribute("data-realce");
      p.style.removeProperty("stroke");
      p.style.removeProperty("stroke-width");
    });
    if (!foco) return;
    const p = el.querySelector<SVGPathElement>(`path[data-id="${foco}"]`);
    if (p) {
      p.setAttribute("data-realce", "");
      p.style.stroke = "var(--foreground)";
      p.style.strokeWidth = "2.5";
    }
  }, [foco]);

  const animar = (anos: number[]) => {
    if (reduzido || anos.length < 2) return;
    let i = 0;
    setAnoEscolhido(anos[0]);
    const t = setInterval(() => {
      i++;
      if (i >= anos.length) return clearInterval(t);
      setAnoEscolhido(anos[i]);
    }, 900);
  };

  const daVez = pontos.length > 0 ? pontos[passo % pontos.length] : null;
  const vals = ufs.map((u) => camada.valor(u.uf, ano)).filter((v): v is number => v != null);
  const [mn, mx] = vals.length ? [Math.min(...vals), Math.max(...vals)] : [null, null];
  const limites = mn != null && mx != null ? [mn, ...cortes, mx] : [];
  const escolhida = foco ? ufs.find((u) => u.uf === foco) : undefined;
  const ordenada = ordenarDoMaior(ufs.map((u) => ({ uf: u.uf, nome: u.nome, valor: camada.valor(u.uf, ano) })));

  const botaoAbrir = (id: "numero" | "comparar" | "lista", rotulo: string) => (
    <button
      type="button"
      aria-expanded={aberto === id}
      onClick={() => setAberto((a) => (a === id ? null : id))}
      className={`min-h-10 border px-3 text-sm ${aberto === id ? "border-foreground font-semibold" : "border-border bg-card hover:border-foreground"}`}
    >
      {rotulo}
    </button>
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="flex items-center gap-2 text-xs font-semibold tracking-wider uppercase" style={{ color: `var(--tema-${camada.tema})` }}>
          <span aria-hidden className="size-2.5" style={{ background: `var(--tema-${camada.tema})` }} />
          {camada.grupo}
        </p>
        <h3 className="text-xl leading-snug" aria-live="polite">
          {camada.titulo}
          {ano && !camada.titulo.endsWith(String(ano)) ? `, ${ano}` : ""}
        </h3>
      </div>

      <div
        ref={caixa}
        className="relative mx-auto w-full max-w-[26rem]"
        // Só some quando a pessoa escolhe um estado (rolar a página com o dedo sobre o mapa
        // também dispara pointerdown, e a mão sumia antes de ser vista).
        onClickCapture={() => setTocou(true)}
        onKeyDownCapture={(e) => {
          if (e.key === "Enter" || e.key === " ") setTocou(true);
        }}
      >
        <MapaBrasil
          niveis="uf"
          className="mx-auto h-[320px] w-full md:h-[380px]"
          titulo={`Mapa dos estados do Brasil: ${camada.titulo}`}
          toqueUnico={false}
          onNavegar={({ uf }) => uf && router.push(`/estado/${uf}`)}
          onSelecionar={(a) => {
            setSel(a?.id ?? null);
            if (a) setTocou(true);
          }}
          classe={(_n, id): ClasseMapa => classe(camada.valor(id, ano), cortes)}
          rotulo={(_n, id) => {
            const v = camada.valor(id, ano);
            return `${NOMES[id] ?? id}: ${v == null ? "sem dado" : camada.formatar(v)}`;
          }}
          resumo={(_n, id) => {
            const v = camada.valor(id, ano);
            return (
              <span className="flex flex-col text-sm">
                <strong>{NOMES[id] ?? id}</strong>
                <span>{v == null ? "sem dado" : camada.formatar(v)}</span>
              </span>
            );
          }}
        />
        {daVez && (
          <svg aria-hidden="true" className="pointer-events-none absolute left-0 top-0 z-10 size-px overflow-visible">
            <MaoToque
              x={daVez.x}
              y={daVez.y}
              oculta={tocou}
              reduzido={reduzido || passo >= 3 * pontos.length - 1}
              etiquetaEsquerda={daVez.x > daVez.largura * 0.55}
            />
          </svg>
        )}
      </div>

      {limites.length > 0 && (
        <div className={`${estilos.caixa} flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground`}>
          <span>{camada.formatar(limites[0])}</span>
          <span className="flex overflow-hidden ring-1 ring-border" aria-hidden>
            {[1, 2, 3, 4, 5].map((c) => (
              <span key={c} className="h-3 w-6" style={{ background: `var(--mapa-${c})` }} />
            ))}
          </span>
          <span>{camada.formatar(limites[limites.length - 1])}</span>
          <span className="basis-full">Mais escuro = número maior (não quer dizer melhor nem pior).</span>
        </div>
      )}

      {camada.anos.length > 1 && (
        <label className="flex max-w-full min-w-0 flex-wrap items-center gap-2 text-sm">
          Ano
          <input
            type="range"
            min={0}
            max={camada.anos.length - 1}
            value={Math.max(0, camada.anos.indexOf(ano ?? camada.anos[camada.anos.length - 1]))}
            onChange={(e) => setAnoEscolhido(camada.anos[Number(e.target.value)])}
            className="w-40 max-w-full min-w-0 accent-[var(--bronze)]"
            aria-valuetext={String(ano)}
          />
          <span className="numero">{ano}</span>
          <span className="text-xs text-muted-foreground">
            de {camada.anos[0]} a {camada.anos[camada.anos.length - 1]}
          </span>
        </label>
      )}

      <div aria-live="polite">
        {escolhida ? (
          <div className="flex flex-col gap-2 border-l-4 bg-card p-3 text-sm" style={{ borderLeftColor: `var(--tema-${camada.tema})` }}>
            <p>
              <strong className="text-base">{escolhida.nome}</strong>:{" "}
              {(() => {
                const v = camada.valor(escolhida.uf, ano);
                return v == null ? "sem dado" : camada.formatar(v);
              })()}
              {cmp &&
                (() => {
                  const v = cmp.valor(escolhida.uf, anoCmp);
                  return ` · ${minuscula(cmp.rotulo)}: ${v == null ? "sem dado" : cmp.formatar(v)}`;
                })()}
            </p>
            <Link href={`/estado/${escolhida.uf}`} className="self-start underline underline-offset-4">
              Tudo sobre {escolhida.nome}
            </Link>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <p className="text-xs text-muted-foreground">Perguntas para começar</p>
        <ul className="flex flex-wrap gap-1.5">
          {PERGUNTAS.filter((p) => camadas.some((c) => c.id === p.camada) && (!p.comparar || camadas.some((c) => c.id === p.comparar))).map((p) => (
            <li key={p.texto}>
              <button
                type="button"
                onClick={() => {
                  escolherCamada(p.camada);
                  setCmpId(p.comparar ?? "");
                  setAberto(p.comparar ? "comparar" : null);
                  const c = camadas.find((x) => x.id === p.camada);
                  if (p.ano === "primeiro" && c) animar(c.anos);
                }}
                className="min-h-10 border border-border bg-card px-3 py-1.5 text-left text-sm hover:border-foreground"
              >
                {p.texto}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {botaoAbrir("numero", "Mudar o número")}
        {botaoAbrir("comparar", cmp ? "Comparação" : "Comparar com outro número")}
        {botaoAbrir("lista", "Ver em lista")}
      </div>

      {aberto === "numero" && (
        <div className="flex flex-col gap-2 border border-border bg-card p-3">
          <Segmentado
            rotulo="Assunto do mapa"
            opcoes={grupos.map((g) => ({ valor: g, rotulo: g }))}
            valor={camada.grupo}
            aoMudar={(g) => escolherCamada(camadas.find((c) => c.grupo === g)!.id)}
          />
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="O que colorir no mapa">
            {camadas
              .filter((c) => c.grupo === camada.grupo)
              .map((c) => (
                <button
                  key={c.id}
                  type="button"
                  aria-pressed={c.id === camada.id}
                  onClick={() => escolherCamada(c.id)}
                  className={`inline-flex min-h-10 items-center gap-2 border px-3 text-sm ${
                    c.id === camada.id ? "border-foreground font-semibold" : "border-border bg-background"
                  }`}
                >
                  <span aria-hidden className="size-2.5" style={{ background: `var(--tema-${c.tema})` }} />
                  {c.rotulo}
                </button>
              ))}
          </div>
        </div>
      )}

      {aberto === "comparar" && (
        <div className="flex flex-col gap-2">
          <label className="flex max-w-full min-w-0 flex-wrap items-center gap-2 text-sm">
            Comparar {minuscula(camada.rotulo)} com
            <select
              value={cmp?.id ?? ""}
              onChange={(e) => setCmpId(e.target.value)}
              className="min-h-10 w-[13rem] max-w-full min-w-0 border border-border bg-card px-2"
            >
              <option value="">escolha um número</option>
              {camadas
                .filter((c) => c.id !== camada.id)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.grupo}: {c.rotulo}
                  </option>
                ))}
            </select>
          </label>
          {cmp && <Dispersao ufs={ufs} x={camada} y={cmp} anoX={ano} anoY={anoCmp} realce={foco} aoRealcar={setRealce} />}
        </div>
      )}

      {aberto === "lista" && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-muted-foreground">
            Em ordem do maior para o menor: {minuscula(camada.rotulo)}
            {ano ? `, ${ano}` : ""}. Estados sem dado no fim.
          </p>
          <ol className="flex flex-col">
            {ordenada.map((u) => (
              <li key={u.uf} className="grid grid-cols-[1fr_auto] gap-3 border-b border-border py-1.5 text-sm">
                <Link href={`/estado/${u.uf}`} className="underline-offset-4 hover:underline">
                  {u.nome}
                </Link>
                <span className="numero">{u.valor == null ? "sem dado" : camada.formatar(u.valor)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Fonte: {camada.fonte}
        {cmp && aberto === "comparar" && cmp.fonte !== camada.fonte ? `; ${cmp.fonte}` : ""}.{camada.nota ? ` ${camada.nota}` : ""}
      </p>
    </div>
  );
}
