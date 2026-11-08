"use client";

/**
 * Entradas que abrem a gaveta "Avisar um erro" (Frente 7): junto da fonte de cada seção
 * (`EntradaRodape`, dentro do `FonteRodape`), ao lado de cada item do checklist (`EntradaItem`)
 * e no fim do perfil (`FimDoPerfil`). Fora de um perfil (sem provider) nada aparece.
 */
import { useEffect, useRef, useState } from "react";

import { useAvisarErro } from "@/components/avisar-erro/contexto";
import { ANCORA_RESPOSTAS, normalizarSecao } from "@/lib/avisar-erro";

function IconeBandeira({ tamanho = 18 }: { tamanho?: number }) {
  return (
    <svg
      aria-hidden
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 21V4M5 4h11l-2 4 2 4H5" />
    </svg>
  );
}

/** Título da seção (h2) que contém o elemento, ou `null` fora de uma seção com título. */
function tituloDaSecao(el: Element | null): string | null {
  const secao = el?.closest("section[aria-labelledby]");
  const id = secao?.getAttribute("aria-labelledby");
  return (id ? document.getElementById(id)?.textContent?.trim() : null) || null;
}

/** "Achou um erro neste número?", no rodapé da fonte de cada seção. A seção vem do próprio lugar da página. */
export function EntradaRodape() {
  const contexto = useAvisarErro();
  const raiz = useRef<HTMLDivElement>(null);
  const [secao, setSecao] = useState<string | null>(null);

  useEffect(() => {
    setSecao(tituloDaSecao(raiz.current));
  }, []);

  if (!contexto) return null;
  const temResposta = !!secao && contexto.secoesComResposta.has(normalizarSecao(secao));

  return (
    <div ref={raiz} className="flex flex-wrap items-center gap-x-4">
      <button
        type="button"
        onClick={(e) => contexto.abrir({ modo: "erro", secao: tituloDaSecao(e.currentTarget) }, e.currentTarget)}
        className="alvo-link gap-2 text-sm text-muted-foreground underline underline-offset-4"
      >
        <IconeBandeira />
        Achou um erro neste número?
      </button>
      {temResposta && (
        <a href={`#${ANCORA_RESPOSTAS}`} className="alvo-link text-sm text-muted-foreground underline underline-offset-4">
          Há uma resposta de quem é citado
        </a>
      )}
    </div>
  );
}

/** Botão pequeno ao lado de cada item do checklist. */
export function EntradaItem({ rotulo }: { rotulo: string }) {
  const contexto = useAvisarErro();
  if (!contexto) return null;
  return (
    <button
      type="button"
      onClick={(e) => contexto.abrir({ modo: "erro", secao: rotulo }, e.currentTarget)}
      className="-my-2 -mr-2 flex size-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--bronze)]"
    >
      <IconeBandeira />
      <span className="sr-only">Avisar erro em {rotulo}</span>
    </button>
  );
}

/** Fim do perfil: sempre visível (não é detalhe), com os dois caminhos. */
export function FimDoPerfil() {
  const contexto = useAvisarErro();
  if (!contexto) return null;
  return (
    <section aria-labelledby="avisar-erro-titulo" data-sem-aviso className="flex flex-col gap-3 border-t border-border pt-[var(--esp-4)]">
      <div>
        <h2 id="avisar-erro-titulo" className="text-2xl">
          Viu algo que não bate?
        </h2>
        <p className="text-sm text-muted-foreground">
          Os dados vêm de fontes oficiais, mas a carga pode ter falha. Avise e uma pessoa confere com a fonte. Quem é citado
          neste perfil também pode pedir que uma resposta fique registrada aqui.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-[var(--esp-2)] min-[26rem]:grid-cols-2">
        <button type="button" onClick={(e) => contexto.abrir({ modo: "erro", secao: null }, e.currentTarget)} className="botao-linha w-full">
          <IconeBandeira />
          Avisar um erro
        </button>
        <button
          type="button"
          onClick={(e) => contexto.abrir({ modo: "resposta", secao: null }, e.currentTarget)}
          className="botao-linha w-full"
        >
          Sou a pessoa deste perfil
        </button>
      </div>
    </section>
  );
}
