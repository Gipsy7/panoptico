"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { type ParlamentarNaLista, getParlamentares } from "@/lib/api";
import { NOME_CASA } from "@/lib/formato";

/**
 * Campo de busca por nome com sugestões. Cada sugestão é um link para
 * `hrefBase + id` (ex.: "/parlamentar/" ou "/comparar?a=3&b=").
 */
export function BuscaParlamentar({
  hrefBase = "/parlamentar/",
  rotulo = "Procure pelo nome",
  ignorarId,
}: {
  hrefBase?: string;
  rotulo?: string;
  ignorarId?: number;
}) {
  const id = useId();
  const [termo, setTermo] = useState("");
  // Resultado guardado junto com o texto que o gerou, para nunca mostrar a resposta de
  // uma busca antiga.
  const [busca, setBusca] = useState<{ texto: string; itens: ParlamentarNaLista[] } | null>(null);
  const ultimaBusca = useRef("");
  const texto = termo.trim();

  useEffect(() => {
    if (texto.length < 3) return;
    const atraso = setTimeout(async () => {
      ultimaBusca.current = texto;
      const resposta = await getParlamentares({ busca: texto });
      if (ultimaBusca.current !== texto) return;
      setBusca({
        texto,
        itens: resposta.ok ? resposta.dados.itens.filter((p) => p.id !== ignorarId) : [],
      });
    }, 300);
    return () => clearTimeout(atraso);
  }, [texto, ignorarId]);

  const resultados = texto.length >= 3 && busca?.texto === texto ? busca.itens : null;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {rotulo}
      </label>
      <input
        id={id}
        type="search"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        placeholder="Ex.: Tabata, Romário"
        autoComplete="off"
        className="h-12 rounded-xl border border-input bg-card px-4 text-base placeholder:text-muted-foreground/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      />
      {resultados !== null && (
        <ul aria-live="polite" className="flex flex-col divide-y rounded-xl bg-card ring-1 ring-foreground/10">
          {resultados.length === 0 ? (
            <li className="p-3 text-sm text-muted-foreground">Ninguém encontrado com esse nome.</li>
          ) : (
            resultados.slice(0, 8).map((p) => (
              <li key={p.id}>
                <Link
                  href={`${hrefBase}${p.id}`}
                  className="flex flex-col p-3 hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                >
                  <span className="font-medium">{p.nome_parlamentar}</span>
                  <span className="text-xs text-muted-foreground">
                    {NOME_CASA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
                  </span>
                </Link>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
