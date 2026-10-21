"use client";

/**
 * "Quem votou" na última votação nominal de um projeto: grupos Sim, Não e outros registros (sempre
 * nessa ordem), partidos de cada grupo e os nomes, com o filtro "do meu estado" e o placar por UF.
 */
import Link from "next/link";
import { useMemo } from "react";

import { PlacarPorUf } from "@/components/placar-por-uf";
import { SeletorUf, useUfEscolhida } from "@/components/uf-escolhida";
import type { GrupoQuemVotou, PorUf } from "@/lib/api";
import { filtrarGruposPorUf } from "@/lib/projetos";
import { UFS } from "@/lib/ufs";

const INTEIRO = new Intl.NumberFormat("pt-BR");

export function QuemVotou({
  grupos,
  porUf,
  ufInicial,
  idSeletor = "uf-quem-votou",
}: {
  grupos: GrupoQuemVotou[];
  porUf: PorUf[];
  ufInicial: string | null;
  idSeletor?: string;
}) {
  const [uf, escolher] = useUfEscolhida(ufInicial);
  const visiveis = useMemo(() => filtrarGruposPorUf(grupos, uf), [grupos, uf]);
  const nomeUf = uf ? (UFS.find((u) => u.sigla === uf)?.nome ?? uf) : null;

  return (
    <div className="flex flex-col gap-5">
      <SeletorUf id={idSeletor} uf={uf} onChange={escolher} rotulo="Ver só quem é do meu estado" />
      {nomeUf && (
        <p className="nota text-sm" aria-live="polite">
          Mostrando só quem representa {nomeUf}.{" "}
          <button type="button" onClick={() => escolher(null)} className="underline underline-offset-4">
            Ver todos
          </button>
        </p>
      )}

      {visiveis.map((g) => (
        <section key={g.chave} aria-label={g.rotulo} className="flex flex-col gap-2">
          <h4 className="text-base font-semibold">
            {g.rotulo} <span className="font-normal text-muted-foreground tabular-nums">({INTEIRO.format(g.quantidade)})</span>
          </h4>
          {g.partidos.length > 0 && (
            <p className="text-sm text-muted-foreground">
              Por partido:{" "}
              {g.partidos.slice(0, 8).map((p, i) => (
                <span key={p.partido} className="tabular-nums">
                  {i > 0 && ", "}
                  {p.partido} {INTEIRO.format(p.quantidade)}
                </span>
              ))}
              {g.partidos.length > 8 && ` e mais ${g.partidos.length - 8} partidos`}
            </p>
          )}
          {g.pessoas.length > 0 ? (
            <details open={Boolean(uf) && g.pessoas.length <= 30}>
              <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
                Ver os {INTEIRO.format(g.pessoas.length)} nomes
              </summary>
              <ul className="lista-fios">
                {g.pessoas.map((p) => (
                  <li key={p.parlamentar_id} className="flex min-h-11 items-center justify-between gap-3 py-2">
                    <span className="flex min-w-0 flex-col">
                      <Link href={`/parlamentar/${p.parlamentar_id}`} className="truncate underline underline-offset-2">
                        {p.nome}
                      </Link>
                      <span className="text-xs text-muted-foreground">
                        {p.partido} · {p.uf}
                      </span>
                    </span>
                    {g.chave === "outros" && (
                      <span className="shrink-0 text-right text-sm text-muted-foreground">{p.registro}</span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          ) : (
            <p className="text-sm text-muted-foreground">{uf ? `Ninguém de ${nomeUf} neste grupo.` : "Ninguém neste grupo."}</p>
          )}
        </section>
      ))}

      <PlacarPorUf porUf={porUf} uf={uf} />
    </div>
  );
}
