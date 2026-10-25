"use client";

import Link from "next/link";
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";

import { type ParlamentarNaLista, getParlamentares } from "@/lib/api";
import { NOME_CASA } from "@/lib/formato";
import { CONTORNO_FOCO, teclarNaBusca } from "@/lib/navegar-links";
import { textoResultados } from "@/lib/opcao-ativa";

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
  const campo = useRef<HTMLInputElement>(null);
  const caixa = useRef<HTMLDivElement>(null);
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

  const aviso = resultados === null ? "" : textoResultados(Math.min(resultados.length, 8), "Ninguém encontrado com esse nome");

  const teclar = (e: KeyboardEvent<HTMLElement>) => teclarNaBusca(e, caixa.current, campo.current);

  return (
    <div ref={caixa} className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {rotulo}
      </label>
      <input
        id={id}
        ref={campo}
        onKeyDown={teclar}
        type="search"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        placeholder="Ex.: Tabata, Romário"
        autoComplete="off"
        className="campo text-base"
      />
      <p role="status" className="sr-only">
        {aviso}
      </p>
      {resultados !== null && (
        <ul className="lista-fios flex flex-col">
          {resultados.length === 0 ? (
            <li className="p-3 text-sm text-muted-foreground">Ninguém encontrado com esse nome.</li>
          ) : (
            resultados.slice(0, 8).map((p) => (
              <li key={p.id}>
                <Link
                  href={`${hrefBase}${p.id}`}
                  className={`flex min-h-11 flex-col p-3 hover:bg-accent ${CONTORNO_FOCO}`}
              onKeyDown={teclar}
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
