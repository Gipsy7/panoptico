"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { FonteRodape } from "@/components/fonte-rodape";
import type { MaisVotados as Dados } from "@/lib/api";
import {
  formatarPct,
  formatarVotos,
  larguraBarra,
  nomeCargoPlural,
} from "@/lib/eleicao";

/** Os 10 deputados mais votados na cidade (versão A, Frente 5), federal e estadual em abas. */
export function MaisVotados({ d }: { d: Dados }) {
  const [aba, setAba] = useState(0);
  const base = useId();
  const cidade = d.municipio?.nome ?? "nesta cidade";
  const atual = d.cargos[aba];
  const maior = atual?.itens[0]?.votos ?? 0;

  return (
    <section aria-labelledby={`${base}-t`} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id={`${base}-t`} className="text-2xl">
          Mais votados em {cidade}, {d.ano}
        </h2>
        <p className="text-sm text-muted-foreground">
          Os 10 deputados com mais votos dados aqui
        </p>
      </div>
      {d.cargos.length > 1 && (
        <div role="tablist" aria-label="Cargo" className="flex flex-wrap gap-2">
          {d.cargos.map((c, i) => (
            <button
              key={c.cargo}
              role="tab"
              id={`${base}-aba-${i}`}
              aria-selected={i === aba}
              aria-controls={`${base}-painel`}
              type="button"
              onClick={() => setAba(i)}
              className={`min-h-11 rounded-[2px] border px-3 text-sm ${i === aba ? "border-foreground font-medium" : "border-border"}`}
            >
              {nomeCargoPlural(c.cargo)}
            </button>
          ))}
        </div>
      )}
      {atual && (
        <div
          role="tabpanel"
          id={`${base}-painel`}
          aria-labelledby={`${base}-aba-${aba}`}
          className="flex flex-col gap-3"
        >
          {atual.pct_em_eleitos !== null &&
            atual.votos_em_eleitos !== null &&
            atual.nominais !== null && (
              <p className="text-sm">
                Dos {formatarVotos(atual.nominais)} votos dados aqui a
                candidatos a {nomeCargoPlural(atual.cargo).toLowerCase()},{" "}
                <strong className="tabular-nums">
                  {formatarPct(atual.pct_em_eleitos, 1)}
                </strong>{" "}
                foram para quem se elegeu (
                {formatarVotos(atual.votos_em_eleitos)} votos).
              </p>
            )}
          <ol className="flex flex-col">
            {atual.itens.map((i) => (
              <li
                key={`${i.posicao}-${i.nome_urna}`}
                className="flex flex-col gap-1 border-b border-border py-2 text-sm"
              >
                <p className="flex items-baseline justify-between gap-2">
                  <span className="min-w-0">
                    <span className="tabular-nums text-muted-foreground">
                      {i.posicao}.{" "}
                    </span>
                    <span className={i.eleito ? "font-semibold" : ""}>
                      {i.candidatura_id ? (
                        <Link
                          href={`/eleito/${i.candidatura_id}`}
                          className="underline underline-offset-2"
                        >
                          {i.nome_urna}
                        </Link>
                      ) : (
                        i.nome_urna
                      )}
                    </span>
                    <span className="text-muted-foreground">
                      {i.partido ? ` · ${i.partido}` : ""} ·{" "}
                      {i.eleito ? "eleito" : "não se elegeu"}
                    </span>
                  </span>
                  <span className="shrink-0 text-right tabular-nums">
                    {formatarVotos(i.votos)}{" "}
                    <span className="text-xs text-muted-foreground">
                      ({formatarPct(i.pct, 1)})
                    </span>
                  </span>
                </p>
                <span
                  aria-hidden
                  className="block h-1.5 w-full overflow-hidden rounded-[2px] bg-muted"
                >
                  <span
                    className="block h-full rounded-[2px] bg-bronze"
                    style={{ width: `${larguraBarra(i.votos, maior)}%` }}
                  />
                </span>
              </li>
            ))}
          </ol>
          <p className="text-xs text-muted-foreground">
            % sobre os votos dados aqui a candidatos (sem legenda, brancos e
            nulos). &ldquo;Eleito&rdquo; vale para o estado inteiro.
          </p>
        </div>
      )}
      <FonteRodape
        fonte={d.fonte_nome}
        url={d.fonte_url}
        atualizadoEm={d.atualizado_em}
      />
    </section>
  );
}
