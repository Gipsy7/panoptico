"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { type ResultadoBusca, getBusca } from "@/lib/api";

/** Busca por nome em todos os níveis: Congresso, Executivo, assembleias e câmaras. */
export function BuscaGeral({ rotulo = "Procure pelo nome" }: { rotulo?: string }) {
  const id = useId();
  const [termo, setTermo] = useState("");
  // Resultado guardado junto com o texto que o gerou, para nunca mostrar a resposta de
  // uma busca antiga.
  const [busca, setBusca] = useState<{ texto: string; itens: ResultadoBusca[] } | null>(null);
  const ultimaBusca = useRef("");
  const texto = termo.trim();

  useEffect(() => {
    if (texto.length < 3) return;
    const atraso = setTimeout(async () => {
      ultimaBusca.current = texto;
      const resposta = await getBusca(texto);
      if (ultimaBusca.current !== texto) return;
      setBusca({ texto, itens: resposta.ok ? resposta.dados.itens : [] });
    }, 300);
    return () => clearTimeout(atraso);
  }, [texto]);

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
        placeholder="Ex.: Tabata, nome do prefeito ou de um vereador"
        autoComplete="off"
        className="campo text-base"
      />
      {resultados !== null && (
        <ul aria-live="polite" className="lista-fios flex flex-col">
          {resultados.length === 0 ? (
            <li className="p-3 text-sm text-muted-foreground">Ninguém encontrado com esse nome.</li>
          ) : (
            resultados.map((r) => (
              <li key={r.caminho}>
                <Link
                  href={r.caminho}
                  className="flex flex-col p-3 hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                >
                  <span className="font-medium">{r.nome}</span>
                  {r.nome_completo && <span className="text-xs text-muted-foreground">{r.nome_completo}</span>}
                  <span className="text-xs text-muted-foreground">
                    {[r.cargo, r.partido, r.lugar].filter(Boolean).join(" · ")}
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
