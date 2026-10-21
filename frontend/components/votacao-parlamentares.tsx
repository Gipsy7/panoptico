"use client";

/**
 * Como votou cada parlamentar numa votação: agrupado por partido (na ordem do tamanho da
 * bancada nesta votação) ou por estado (alfabética), com busca por nome, partido ou UF.
 * Sem JavaScript, a lista inteira aparece agrupada por partido.
 */
import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { PlacarPorUf } from "@/components/placar-por-uf";
import { SeletorUf, useUfEscolhida } from "@/components/uf-escolhida";
import type { ParlamentarNaVotacao, PorUf } from "@/lib/api";
import { UFS } from "@/lib/ufs";

function chave(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function VotacaoParlamentares({
  parlamentares,
  ordemPartidos,
  casa,
  porUf = [],
  ufInicial = null,
}: {
  parlamentares: ParlamentarNaVotacao[];
  ordemPartidos: string[];
  casa: "camara" | "senado";
  /** Placar por estado (Sim, Não, outros), quando a API traz. */
  porUf?: PorUf[];
  /** Estado vindo de `?uf=`; sem ele, vale o que o aparelho lembrou. */
  ufInicial?: string | null;
}) {
  const [uf, escolherUf] = useUfEscolhida(ufInicial);
  const [busca, setBusca] = useState("");
  const [agrupar, setAgrupar] = useState<"partido" | "uf">("partido");
  const termo = chave(useDeferredValue(busca).trim());

  const grupos = useMemo(() => {
    const doEstado = uf ? parlamentares.filter((p) => p.uf === uf) : parlamentares;
    const filtrados = termo
      ? doEstado.filter((p) => chave(`${p.nome} ${p.partido} ${p.uf}`).includes(termo))
      : doEstado;
    const mapa = new Map<string, ParlamentarNaVotacao[]>();
    for (const p of filtrados) {
      const g = agrupar === "partido" ? p.partido : p.uf;
      if (!mapa.has(g)) mapa.set(g, []);
      mapa.get(g)!.push(p);
    }
    const ordem =
      agrupar === "partido"
        ? ordemPartidos.filter((g) => mapa.has(g))
        : [...mapa.keys()].sort((a, b) => a.localeCompare(b, "pt-BR"));
    return { total: filtrados.length, lista: ordem.map((g) => ({ nome: g, itens: mapa.get(g)! })) };
  }, [parlamentares, ordemPartidos, termo, agrupar, uf]);

  const quem = casa === "camara" ? "deputado" : "senador";
  const nomeUf = uf ? (UFS.find((u) => u.sigla === uf)?.nome ?? uf) : null;

  return (
    <div className="flex flex-col gap-4">
      <SeletorUf id="uf-votacao" uf={uf} onChange={escolherUf} rotulo="Ver só quem é do meu estado" />
      <PlacarPorUf porUf={porUf} uf={uf} />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          Buscar por nome, partido ou estado
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder={`Ex.: nome do ${quem}, PT, SP`}
            className="campo w-full"
          />
        </label>
        <fieldset className="flex flex-col gap-1 text-sm">
          <legend className="mb-1">Agrupar por</legend>
          <div className="flex gap-2">
            {(
              [
                ["partido", "Partido"],
                ["uf", "Estado"],
              ] as const
            ).map(([valor, rotulo]) => (
              <button
                key={valor}
                type="button"
                aria-pressed={agrupar === valor}
                onClick={() => setAgrupar(valor)}
                className={`botao-linha ${agrupar === valor ? "border-foreground font-semibold" : "text-muted-foreground"}`}
              >
                {rotulo}
              </button>
            ))}
          </div>
        </fieldset>
      </div>
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {grupos.total.toLocaleString("pt-BR")} {grupos.total === 1 ? "registro" : "registros"}
        {nomeUf && ` de ${nomeUf}`}
        {termo && ` para "${busca.trim()}"`}
      </p>
      {grupos.lista.map((g) => (
        <section key={g.nome} aria-label={g.nome} className="flex flex-col gap-1">
          <h4 className="text-base font-semibold">
            {g.nome} <span className="font-normal text-muted-foreground">({g.itens.length})</span>
          </h4>
          <ul className="lista-fios">
            {g.itens.map((p) => (
              <li key={p.parlamentar_id} className="flex min-h-11 items-center justify-between gap-3 py-2">
                <span className="flex min-w-0 flex-col">
                  <Link href={`/parlamentar/${p.parlamentar_id}`} className="truncate underline underline-offset-2">
                    {p.nome}
                  </Link>
                  <span className="text-xs text-muted-foreground">
                    {agrupar === "partido" ? p.uf : p.partido}
                  </span>
                </span>
                <span className={`shrink-0 text-right text-sm ${p.efetivo ? "font-semibold" : "text-muted-foreground"}`}>
                  {p.registro}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
