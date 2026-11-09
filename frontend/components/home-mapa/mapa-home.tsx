"use client";

// Mapa da home: um convite ao Mapa completo. Só os símbolos de assunto da tela completa (dinheiro
// da União, segurança, saúde, saneamento, escolas, economia), que trocam as cores dos estados; a
// legenda diz o que a cor mostra. Tocar num estado (ou no botão) abre o Mapa completo já naquele
// estado e assunto. No computador o resumo segue o mouse; no celular o 1º toque mostra o resumo e o
// 2º abre o Mapa.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { IconeAssunto } from "@/components/icone-assunto";
import { MaoToque, useMovimentoReduzido } from "@/components/mao-toque";
import { MapaBrasil } from "@/components/mapa/mapa-brasil";
import estilos from "@/components/mapa/mapa-brasil.module.css";
import type { IndicadoresUfs } from "@/lib/api";
import { ASSUNTOS_MAPA, type AssuntoMapa } from "@/lib/assuntos-mapa";
import { anoDaCamada, montarCamadas, type UfDinheiro } from "@/lib/camadas-mapa";
import { classe, quantis, type ClasseMapa } from "@/lib/mapa";

export type UfDoMapa = UfDinheiro;

// Estados por onde a mão passeia: grandes e espalhados, o primeiro bem visível no celular.
const ROTEIRO_MAO = ["PA", "BA", "AM", "MG", "MT", "RS"];

/** Camada da home para cada assunto (dinheiro: quanto volta a cada R$ 100 arrecadados). */
const CAMADA_DO_ASSUNTO: Record<AssuntoMapa["id"], string> = {
  dinheiro: "retorno",
  seguranca: "homicidios",
  saude: "leitos",
  saneamento: "esgoto",
  escolas: "ideb",
  economia: "pib",
};

interface PontoMao {
  uf: string;
  x: number;
  y: number;
  largura: number;
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
  const nomes = useMemo(() => Object.fromEntries(ufs.map((u) => [u.uf, u.nome])) as Record<string, string>, [ufs]);
  const camadas = useMemo(
    () => montarCamadas(ufs, indicadores, anoDinheiro, fonteDinheiro, fonteObras),
    [ufs, indicadores, anoDinheiro, fonteDinheiro, fonteObras],
  );
  const assuntos = ASSUNTOS_MAPA.filter((a) => camadas.some((c) => c.id === CAMADA_DO_ASSUNTO[a.id]));
  const [tema, setTema] = useState<AssuntoMapa["id"]>(assuntos.some((a) => a.id === "seguranca") ? "seguranca" : "dinheiro");
  const assunto = assuntos.find((a) => a.id === tema) ?? assuntos[0];
  const camada = camadas.find((c) => c.id === CAMADA_DO_ASSUNTO[assunto.id])!;
  const ano = anoDaCamada(camada, null);
  const cortes = quantis(ufs.map((u) => camada.valor(u.uf, ano)));
  const caixa = useRef<HTMLDivElement>(null);
  const [pontos, setPontos] = useState<PontoMao[]>([]);
  const [tocou, setTocou] = useState(false);
  const [passo, setPasso] = useState(0);
  const reduzido = useMovimentoReduzido();
  const destino = (uf?: string) => `/impostos-e-repasses${uf ? `/${uf}` : ""}${assunto.id !== "dinheiro" ? `?tema=${assunto.id}` : ""}`;

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

  const daVez = pontos.length > 0 ? pontos[passo % pontos.length] : null;
  const vals = ufs.map((u) => camada.valor(u.uf, ano)).filter((v): v is number => v != null);
  const [mn, mx] = vals.length ? [Math.min(...vals), Math.max(...vals)] : [null, null];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-6 gap-1.5" role="group" aria-label="Assunto do mapa">
        {assuntos.map((a) => (
          <button
            key={a.id}
            type="button"
            aria-pressed={a.id === assunto.id}
            aria-label={a.nome}
            title={a.nome}
            onClick={() => setTema(a.id)}
            className={`flex min-h-14 flex-col items-center justify-center gap-1 border px-1 text-xs ${
              a.id === assunto.id ? "border-foreground font-semibold" : "border-border bg-card hover:border-foreground"
            }`}
            style={a.id === assunto.id ? { boxShadow: `inset 0 -3px 0 var(--tema-${a.tema})` } : undefined}
          >
            <span style={{ color: `var(--tema-${a.tema})` }}>
              <IconeAssunto assunto={a.icone} className="size-6" />
            </span>
            <span className="hidden truncate sm:block">{a.nome}</span>
          </button>
        ))}
      </div>

      <p className="text-sm font-semibold" aria-live="polite">
        {camada.titulo}
        {ano && !camada.titulo.endsWith(String(ano)) ? `, ${ano}` : ""}
      </p>

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
          titulo={`Mapa dos estados do Brasil: ${camada.titulo}. Toque num estado para abrir o Mapa completo.`}
          toqueUnico={false}
          onNavegar={({ uf }) => uf && router.push(destino(uf))}
          onSelecionar={(a) => a && setTocou(true)}
          classe={(_n, id): ClasseMapa => classe(camada.valor(id, ano), cortes)}
          rotulo={(_n, id) => {
            const v = camada.valor(id, ano);
            return `${nomes[id] ?? id}: ${v == null ? "sem dado" : camada.formatar(v)}`;
          }}
          resumo={(_n, id) => {
            const v = camada.valor(id, ano);
            return (
              <span className="flex flex-col text-sm">
                <strong>{nomes[id] ?? id}</strong>
                <span>{v == null ? "sem dado" : camada.formatar(v)}</span>
                <span className="text-muted-foreground">Toque de novo para abrir no Mapa</span>
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

      {mn != null && mx != null && (
        <div className={`${estilos.caixa} flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground`}>
          <span>{camada.formatar(mn)}</span>
          <span className="flex overflow-hidden ring-1 ring-border" aria-hidden>
            {[1, 2, 3, 4, 5].map((c) => (
              <span key={c} className="h-3 w-6" style={{ background: `var(--mapa-${c})` }} />
            ))}
          </span>
          <span>{camada.formatar(mx)}</span>
          <span className="basis-full">Mais escuro = número maior (não quer dizer melhor nem pior). Fonte: {camada.fonte}.</span>
        </div>
      )}

      <Link href={destino()} className="botao-linha group self-start">
        <IconeAssunto assunto="lugar" className="size-4 text-bronze" />
        Abrir o Mapa completo: estados, cidades e quem as representa
        <span aria-hidden className="transition-transform group-hover:translate-x-0.5">
          →
        </span>
      </Link>
    </div>
  );
}
