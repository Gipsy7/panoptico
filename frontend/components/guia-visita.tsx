"use client";

/**
 * Guia da primeira visita: linha do tempo de 3 passos colada logo abaixo do cabeçalho; cada passo
 * acende conforme a pessoa rola a página. Aparece uma vez por aparelho (localStorage, com
 * try/catch), some ao fechar (×) ou ao chegar ao fim da página. Fica por cima do conteúdo
 * (posição absoluta no cabeçalho) para não empurrar nada quando aparece. Na página inicial é o
 * guia geral; num perfil aberto por link, a versão adaptada. Enquanto está na tela, marca o
 * <html> para a dica da página esperar (lib/guia-visita.ts, ATRIBUTO_GUIA_VISIVEL).
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ATRIBUTO_GUIA_VISIVEL,
  CHAVE_GUIA_VISTO,
  chegouAoFim,
  guiaJaVisto,
  passoDoProgresso,
  passosDoGuia,
  progressoDeRolagem,
  REGRA_GUIA,
  tipoDeGuia,
} from "@/lib/guia-visita";

export function GuiaVisita() {
  const caminho = usePathname();
  const tipo = tipoDeGuia(caminho);
  const [visto, setVisto] = useState<boolean | null>(null);
  const [progresso, setProgresso] = useState(0);

  // Lê o que o aparelho lembrou (só no cliente, depois de montar: sem empurrar o conteúdo).
  useEffect(() => {
    const quadro = requestAnimationFrame(() => {
      try {
        setVisto(guiaJaVisto(window.localStorage.getItem(CHAVE_GUIA_VISTO)));
      } catch {
        // Armazenamento bloqueado: mostra nesta visita e não lembra.
        setVisto(false);
      }
    });
    return () => cancelAnimationFrame(quadro);
  }, []);

  const visivel = tipo !== null && visto === false;

  function dispensar() {
    setVisto(true);
    try {
      window.localStorage.setItem(CHAVE_GUIA_VISTO, "1");
    } catch {
      // Sem armazenamento: só não lembra.
    }
  }

  // Avisa a dica da página que o guia está na tela.
  useEffect(() => {
    const raiz = document.documentElement;
    if (visivel) raiz.setAttribute(ATRIBUTO_GUIA_VISIVEL, "1");
    else raiz.removeAttribute(ATRIBUTO_GUIA_VISIVEL);
    return () => raiz.removeAttribute(ATRIBUTO_GUIA_VISIVEL);
  }, [visivel]);

  // Acompanha a rolagem; ao chegar ao fim da página, o guia sai e não volta.
  useEffect(() => {
    if (!visivel) return;
    let quadro = 0;
    const medir = () => {
      quadro = 0;
      const doc = document.documentElement;
      const p = progressoDeRolagem(window.scrollY, doc.scrollHeight, window.innerHeight);
      setProgresso(p);
      if (chegouAoFim(p)) {
        setVisto(true);
        try {
          window.localStorage.setItem(CHAVE_GUIA_VISTO, "1");
        } catch {
          // Sem armazenamento: só não lembra.
        }
      }
    };
    const aoRolar = () => {
      if (!quadro) quadro = requestAnimationFrame(medir);
    };
    quadro = requestAnimationFrame(medir);
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => {
      window.removeEventListener("scroll", aoRolar);
      if (quadro) cancelAnimationFrame(quadro);
    };
  }, [visivel, caminho]);

  if (!visivel || tipo === null) return null;

  const passos = passosDoGuia(tipo);
  const atual = passoDoProgresso(progresso, passos.length);

  return (
    <section
      aria-label={tipo === "geral" ? "Como usar o Panóptico, em 3 passos" : "Como ler este perfil, em 3 passos"}
      className="absolute inset-x-0 top-full border-b border-border bg-background py-2 pr-14 pl-3 shadow-[var(--sombra-menu)] print:hidden"
    >
      <ol className="relative mx-auto grid max-w-3xl grid-cols-3">
        <span
          aria-hidden
          className="absolute top-[13px] right-[16.6%] left-[16.6%] h-0.5 bg-border"
        />
        <span
          aria-hidden
          className="absolute top-[13px] left-[16.6%] h-0.5 bg-bronze transition-[width] duration-300 motion-reduce:transition-none"
          style={{ width: `${(atual / (passos.length - 1)) * 66.8}%` }}
        />
        {passos.map((p, i) => {
          const feito = i < atual;
          const aceso = i === atual;
          return (
            <li
              key={p.rotulo}
              aria-current={aceso ? "step" : undefined}
              className={`relative text-center text-[0.8125rem] leading-tight ${
                aceso ? "font-semibold text-foreground" : "text-muted-foreground"
              }`}
            >
              <span
                aria-hidden
                className={`mx-auto mb-0.5 grid size-7 place-items-center rounded-full border-2 bg-background font-heading text-[0.95rem] transition-colors duration-200 motion-reduce:transition-none ${
                  aceso
                    ? "border-primary bg-primary text-primary-foreground"
                    : feito
                      ? "border-bronze text-bronze-texto"
                      : "border-border text-muted-foreground"
                }`}
              >
                {i + 1}
              </span>
              <span className="sr-only">Passo {i + 1}: </span>
              {p.rotulo}
            </li>
          );
        })}
      </ol>
      <p className="mx-auto mt-1.5 max-w-3xl text-sm leading-snug" aria-live="polite">
        {passos[atual].frase}
        {tipo === "perfil" && atual === 0 ? (
          <>
            {" "}
            <Link href="/#cep" className="font-medium underline underline-offset-2">
              Escolher a cidade
            </Link>
          </>
        ) : null}
      </p>
      <p className="mx-auto mt-0.5 max-w-3xl text-[0.8125rem] leading-snug text-muted-foreground">
        {REGRA_GUIA}
      </p>
      <button
        type="button"
        onClick={dispensar}
        aria-label="Fechar o guia"
        className="absolute top-1 right-0 flex min-h-11 min-w-11 items-center justify-center text-2xl leading-none text-foreground focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-bronze-texto"
      >
        <span aria-hidden>×</span>
      </button>
    </section>
  );
}
