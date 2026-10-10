"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { type RespostaBusca, type ResultadoBusca, getBusca } from "@/lib/api";

/** Com 2 letras só dá para achar a sigla de um partido ("PT"); nomes pedem 3. */
const MINIMO = 2;

function Pessoas({ titulo, itens }: { titulo: string; itens: ResultadoBusca[] }) {
  if (itens.length === 0) return null;
  return (
    <section aria-label={titulo} className="flex flex-col gap-1">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{titulo}</h3>
      <ul className="lista-fios flex flex-col">
        {itens.map((r) => (
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
        ))}
      </ul>
    </section>
  );
}

/** Busca por nome: Congresso, Executivo, assembleias, câmaras, partidos e eleitos de antes. */
export function BuscaGeral({ rotulo = "Procure pelo nome" }: { rotulo?: string }) {
  const id = useId();
  const [termo, setTermo] = useState("");
  // Resultado guardado junto com o texto que o gerou, para nunca mostrar a resposta de
  // uma busca antiga.
  const [busca, setBusca] = useState<{ texto: string; resposta: RespostaBusca } | null>(null);
  const ultimaBusca = useRef("");
  const texto = termo.trim();

  useEffect(() => {
    if (texto.length < MINIMO) return;
    const atraso = setTimeout(async () => {
      ultimaBusca.current = texto;
      const resposta = await getBusca(texto);
      if (ultimaBusca.current !== texto) return;
      setBusca({ texto, resposta: resposta.ok ? resposta.dados : { itens: [], partidos: [], pessoas: [], eleitos_2026: [] } });
    }, 300);
    return () => clearTimeout(atraso);
  }, [texto]);

  const resultados = texto.length >= MINIMO && busca?.texto === texto ? busca.resposta : null;
  const vazio = resultados && !resultados.itens.length && !resultados.partidos.length && !resultados.pessoas.length && !resultados.eleitos_2026.length;

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
        placeholder="Ex.: Tabata, nome do prefeito, de um vereador ou sigla de partido"
        autoComplete="off"
        className="campo text-base"
      />
      {resultados && (
        <div aria-live="polite" className="flex flex-col gap-3">
          {vazio && <p className="p-3 text-sm text-muted-foreground">Nada encontrado com esse nome.</p>}
          <Pessoas titulo="No cargo hoje" itens={resultados.itens} />
          {resultados.partidos.length > 0 && (
            <section aria-label="Partidos" className="flex flex-col gap-1">
              <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Partidos</h3>
              <ul className="lista-fios flex flex-col">
                {resultados.partidos.map((p) => (
                  <li key={p.caminho}>
                    <Link
                      href={p.caminho}
                      className="flex flex-col p-3 hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                    >
                      <span className="font-medium">{p.sigla}</span>
                      <span className="text-xs text-muted-foreground">{p.nome} · contas e dinheiro público</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <Pessoas titulo="Eleitos em 2026, ainda sem posse" itens={resultados.eleitos_2026} />
          <Pessoas titulo="Eleições passadas e suplentes" itens={resultados.pessoas} />
        </div>
      )}
    </div>
  );
}
