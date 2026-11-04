"use client";

/**
 * Índice de /dicionario: busca que filtra no próprio aparelho (sem acento, sem maiúscula), A–Z e
 * a lista. Cada termo tem âncora (/dicionario#cota) e abre a explicação completa num <details>;
 * chegar pela âncora (o "Ver no dicionário" da gaveta) já abre o termo. Sem JavaScript, a lista
 * inteira aparece e os links do A–Z funcionam.
 */
import { useEffect, useId, useMemo, useState } from "react";

import { Explicacao } from "@/components/termo-oficial";
import { type Termo, buscarTermos, letraDoTermo, termosEmOrdem } from "@/lib/dicionario";

const LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

/** Abre o termo da âncora atual e rola até ele. */
function abrirDaAncora() {
  const id = decodeURIComponent(window.location.hash.slice(1));
  if (!id) return;
  const alvo = document.getElementById(id);
  const detalhes = alvo?.querySelector("details");
  if (detalhes) {
    detalhes.open = true;
    alvo?.scrollIntoView({ block: "start" });
  }
}

export function DicionarioIndice() {
  const idBusca = useId();
  const [consulta, setConsulta] = useState("");
  const todos = useMemo(() => termosEmOrdem(), []);
  const achados = useMemo(() => buscarTermos(consulta, todos), [consulta, todos]);
  const comTermo = useMemo(() => new Set(todos.map(letraDoTermo)), [todos]);

  useEffect(() => {
    abrirDaAncora();
    // Âncora nova com a busca escondendo o termo: limpa a busca e abre depois de desenhar.
    const aoMudarAncora = () => {
      setConsulta("");
      setTimeout(abrirDaAncora, 50);
    };
    window.addEventListener("hashchange", aoMudarAncora);
    return () => window.removeEventListener("hashchange", aoMudarAncora);
  }, []);

  const grupos: { letra: string; termos: Termo[] }[] = [];
  for (const t of achados) {
    const l = letraDoTermo(t);
    const ultimo = grupos[grupos.length - 1];
    if (ultimo?.letra === l) ultimo.termos.push(t);
    else grupos.push({ letra: l, termos: [t] });
  }

  const n = achados.length;
  const anuncio = consulta.trim()
    ? n === 0
      ? "Nenhuma palavra encontrada."
      : `${n} ${n === 1 ? "palavra encontrada" : "palavras encontradas"}.`
    : "";

  return (
    <div className="flex flex-col gap-[var(--esp-4)]">
      <div className="flex flex-col gap-[var(--esp-2)]">
        <label htmlFor={idBusca} className="text-sm font-medium">
          Procurar palavra
        </label>
        <input
          id={idBusca}
          type="search"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Ex.: PEC, cota, quórum"
          autoComplete="off"
          className="h-12 w-full rounded-[2px] border border-borda-controle bg-card px-3 text-base focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto"
        />
        <p role="status" className="min-h-5 text-sm text-muted-foreground">
          {anuncio}
        </p>
      </div>

      <nav aria-label="Letras de A a Z">
        <ul className="grid grid-cols-7 gap-1">
          {LETRAS.map((l) => (
            <li key={l}>
              {comTermo.has(l) ? (
                <a
                  href={`#letra-${l}`}
                  onClick={() => setConsulta("")}
                  aria-label={`Palavras com ${l}`}
                  className="flex min-h-11 items-center justify-center rounded-[2px] border border-borda-controle bg-card font-heading text-lg font-semibold hover:bg-[var(--realce-forte)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto"
                >
                  {l}
                </a>
              ) : (
                <span aria-hidden className="flex min-h-11 items-center justify-center rounded-[2px] border border-border font-heading text-lg text-muted-foreground opacity-60">
                  {l}
                </span>
              )}
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex flex-col">
        {grupos.map((g) => (
          <section key={g.letra} id={`letra-${g.letra}`} aria-labelledby={`titulo-letra-${g.letra}`} className="scroll-mt-20">
            <h2 id={`titulo-letra-${g.letra}`} className="mt-[var(--esp-4)] border-b border-border pb-1 font-heading text-3xl leading-none text-bronze-texto">
              {g.letra}
            </h2>
            <ul className="flex flex-col">
              {g.termos.map((t) => (
                <li key={t.id} id={t.id} className="scroll-mt-20 border-b border-border">
                  <details className="group">
                    <summary className="grid min-h-14 cursor-pointer list-none grid-cols-[1fr_auto] gap-x-4 py-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto [&::-webkit-details-marker]:hidden">
                      <h3 className="col-start-1 text-lg font-semibold">{t.termo}</h3>
                      <span aria-hidden className="col-start-2 row-span-3 row-start-1 pt-1 text-xl text-bronze-texto transition-transform duration-200 group-open:rotate-45 motion-reduce:transition-none">
                        +
                      </span>
                      <span className="col-start-1 text-sm text-muted-foreground">{t.oficial}</span>
                      <span className="col-start-1 mt-0.5">{t.resumo}</span>
                    </summary>
                    <div className="pb-[var(--esp-4)]">
                      <Explicacao termo={t} semTitulo />
                    </div>
                  </details>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
