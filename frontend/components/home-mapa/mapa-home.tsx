"use client";

// Mapa da home: só estados, coloridos pelo repasse a cada R$ 100 arrecadados.
// No computador o resumo segue o mouse e o clique abre o estado; no celular o 1º toque
// mostra o resumo logo abaixo e o 2º abre a página do estado.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

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

const REAIS_100 = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

function aCada100(u: UfDoMapa): number | null {
  return u.arrecadacao && u.arrecadacao > 0 && u.repasse != null ? (u.repasse / u.arrecadacao) * 100 : null;
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
        A cada R$ 100 arrecadados: <span className="tabular-nums">{r != null ? REAIS_100.format(r) : "sem dado"}</span>
      </span>
    </div>
  );
}

export function MapaHome({ ufs }: { ufs: UfDoMapa[] }) {
  const router = useRouter();
  const [sel, setSel] = useState<string | null>(null);
  const porUf = useMemo(() => new Map(ufs.map((u) => [u.uf, u])), [ufs]);
  const cortes = useMemo(() => quantis(ufs.map(aCada100)), [ufs]);
  const escolhida = sel ? porUf.get(sel) : undefined;

  return (
    <div className="flex flex-col gap-3">
      <MapaBrasil
        niveis="uf"
        className="mx-auto h-[360px] w-full max-w-[26rem] md:h-[420px]"
        titulo="Mapa dos estados do Brasil, colorido pelo repasse da União a cada R$ 100 arrecadados"
        toqueUnico={false}
        onNavegar={({ uf }) => uf && router.push(`/impostos-e-repasses/${uf}`)}
        onSelecionar={(a) => setSel(a?.id ?? null)}
        classe={(_n, id): ClasseMapa => classe(porUf.get(id) ? aCada100(porUf.get(id)!) : null, cortes)}
        rotulo={(_n, id) => {
          const u = porUf.get(id);
          const r = u ? aCada100(u) : null;
          return u ? `${u.nome}: ${r != null ? `${REAIS_100.format(r)} a cada R$ 100 arrecadados` : "sem dado"}` : id;
        }}
        resumo={(_n, id) => {
          const u = porUf.get(id);
          return u ? <Resumo u={u} /> : id;
        }}
      />
      <div className={`${estilos.caixa} flex items-center gap-2 text-xs text-muted-foreground`} aria-hidden>
        <span>menos</span>
        <span className="flex overflow-hidden rounded-[2px] ring-1 ring-border">
          {[1, 2, 3, 4, 5].map((c) => (
            <span key={c} className="h-3 w-8" style={{ background: `var(--mapa-${c})` }} />
          ))}
        </span>
        <span>mais por R$ 100 arrecadados</span>
      </div>
      <div className="min-h-[7rem] border-t border-border pt-3 md:hidden" aria-live="polite">
        {escolhida ? (
          <div className="flex flex-col gap-2">
            <Resumo u={escolhida} />
            <Link href={`/impostos-e-repasses/${escolhida.uf}`} className="botao-linha self-start">
              Abrir {escolhida.nome}
            </Link>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Toque num estado para ver os números.</p>
        )}
      </div>
    </div>
  );
}
