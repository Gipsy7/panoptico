"use client";

// Mapa da home: só estados, coloridos pelo repasse a cada R$ 100 arrecadados.
// No computador o resumo segue o mouse e o clique abre o estado; no celular o 1º toque
// mostra o resumo logo abaixo e o 2º abre a página do estado.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { MaoToque, useMovimentoReduzido } from "@/components/mao-toque";
import { MapaBrasil } from "@/components/mapa/mapa-brasil";
import estilos from "@/components/mapa/mapa-brasil.module.css";
import { classe, quantis, type ClasseMapa } from "@/lib/mapa";
import { reais } from "@/components/dinheiro-federal/formatos";

export interface UfDoMapa {
  uf: string;
  nome: string;
  arrecadacao: number | null;
  repasse: number | null;
}

const REAIS_100 = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function aCada100(u: UfDoMapa): number | null {
  return u.arrecadacao && u.arrecadacao > 0 && u.repasse != null
    ? (u.repasse / u.arrecadacao) * 100
    : null;
}

function Resumo({ u }: { u: UfDoMapa }) {
  const r = aCada100(u);
  return (
    <div className="flex flex-col gap-0.5 text-sm">
      <strong>{u.nome}</strong>
      <span>
        Arrecadou <span className="tabular-nums">{reais(u.arrecadacao)}</span>
      </span>
      <span>
        Recebeu <span className="tabular-nums">{reais(u.repasse)}</span>
      </span>
      <span>
        A cada R$ 100 arrecadados:{" "}
        <span className="tabular-nums">
          {r != null ? REAIS_100.format(r) : "sem dado"}
        </span>
      </span>
    </div>
  );
}

// Estados por onde a mão passeia: grandes e espalhados, o primeiro bem visível no celular.
const ROTEIRO_MAO = ["PA", "BA", "AM", "MG", "MT", "RS"];

interface PontoMao {
  uf: string;
  x: number;
  y: number;
  largura: number;
}

export function MapaHome({ ufs }: { ufs: UfDoMapa[] }) {
  const router = useRouter();
  const [sel, setSel] = useState<string | null>(null);
  const porUf = useMemo(() => new Map(ufs.map((u) => [u.uf, u])), [ufs]);
  const cortes = useMemo(() => quantis(ufs.map(aCada100)), [ufs]);
  const escolhida = sel ? porUf.get(sel) : undefined;
  const caixa = useRef<HTMLDivElement>(null);
  const [pontos, setPontos] = useState<PontoMao[]>([]);
  const [tocou, setTocou] = useState(false);
  const [passo, setPasso] = useState(0);
  const reduzido = useMovimentoReduzido();

  // Centros dos estados medidos na tela depois de montar (sem JS não há mão, então não há salto).
  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    const medir = () => {
      const base = el.getBoundingClientRect();
      const lista: PontoMao[] = [];
      for (const uf of ROTEIRO_MAO) {
        const p = el.querySelector(`path[data-id="${uf}"]`);
        if (!p) continue;
        const r = p.getBoundingClientRect();
        if (r.width === 0) continue;
        lista.push({
          uf,
          x: r.left - base.left + r.width / 2,
          y: r.top - base.top + r.height / 2,
          largura: base.width,
        });
      }
      setPontos(lista);
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
    const t = setInterval(() => {
      setPasso((i) => {
        if (i >= limite) {
          clearInterval(t);
          return i;
        }
        return i + 1;
      });
    }, 2600);
    return () => clearInterval(t);
  }, [tocou, reduzido, pontos.length]);

  const daVez = pontos.length > 0 ? pontos[passo % pontos.length] : null;

  return (
    <div className="flex flex-col gap-3">
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
          className="mx-auto h-[360px] w-full md:h-[420px]"
          titulo="Mapa dos estados do Brasil, colorido pelo repasse da União a cada R$ 100 arrecadados"
          toqueUnico={false}
          onNavegar={({ uf }) =>
            uf && router.push(`/impostos-e-repasses/${uf}`)
          }
          onSelecionar={(a) => {
            setSel(a?.id ?? null);
            if (a) setTocou(true);
          }}
          classe={(_n, id): ClasseMapa =>
            classe(porUf.get(id) ? aCada100(porUf.get(id)!) : null, cortes)
          }
          rotulo={(_n, id) => {
            const u = porUf.get(id);
            const r = u ? aCada100(u) : null;
            return u
              ? `${u.nome}: ${r != null ? `${REAIS_100.format(r)} a cada R$ 100 arrecadados` : "sem dado"}`
              : id;
          }}
          resumo={(_n, id) => {
            const u = porUf.get(id);
            return u ? <Resumo u={u} /> : id;
          }}
        />
        {daVez && (
          <svg
            aria-hidden="true"
            // 1 px, não 0: o navegador não desenha um <svg> de tamanho zero, nem com overflow visível.
            className="pointer-events-none absolute left-0 top-0 z-10 size-px overflow-visible"
          >
            <MaoToque
              x={daVez.x}
              y={daVez.y}
              oculta={tocou}
              // Fim das 3 voltas: a mão para de pulsar também (WCAG 2.2.2).
              reduzido={reduzido || passo >= 3 * pontos.length - 1}
              etiquetaEsquerda={daVez.x > daVez.largura * 0.55}
            />
          </svg>
        )}
      </div>
      <div
        className={`${estilos.caixa} flex items-center gap-2 text-sm text-muted-foreground`}
        aria-hidden
      >
        <span>menos</span>
        <span className="flex overflow-hidden rounded-[2px] ring-1 ring-border">
          {[1, 2, 3, 4, 5].map((c) => (
            <span
              key={c}
              className="h-3 w-8"
              style={{ background: `var(--mapa-${c})` }}
            />
          ))}
        </span>
        <span>mais por R$ 100 arrecadados</span>
      </div>
      <div
        className="min-h-[7rem] border-t border-border pt-3"
      >
        {escolhida ? (
          <div className="flex flex-col gap-2">
            <Resumo u={escolhida} />
            <Link
              href={`/impostos-e-repasses/${escolhida.uf}`}
              className="botao-linha self-start"
            >
              Abrir {escolhida.nome}
            </Link>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Toque, clique ou use as setas do teclado num estado para ver os números.
          </p>
        )}
        <div className="mt-2 flex">
          <Link href="/impostos-e-repasses?vista=lista" className="botao-linha">
            Ver como lista
          </Link>
        </div>
      </div>
    </div>
  );
}
