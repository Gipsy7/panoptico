"use client";

import { useEffect, useId, useRef, useState } from "react";

import { ArgosChat } from "@/components/argos/argos-chat";
import { tornarFundoInerte } from "@/lib/fundo-inerte";

function Olho({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/**
 * Botão fixo "Pergunte ao Argos" em todas as telas (escondido em /pergunte por CSS: a página traz
 * `data-argos-pagina`). Abre o chat por cima: tela cheia no celular, painel lateral no computador.
 * O chat só é carregado na primeira abertura e, depois, fica na memória (fechado) para a conversa
 * continuar ao mudar de página; nada é gravado. Esc fecha e o foco volta ao botão.
 */
export function ArgosBotao() {
  const idTitulo = useId();
  const [aberto, setAberto] = useState(false);
  const [jaAbriu, setJaAbriu] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);
  const painel = useRef<HTMLDivElement>(null);
  const devolverFoco = useRef(false);

  function abrir() {
    setJaAbriu(true);
    setAberto(true);
  }

  function fechar(comFoco: boolean) {
    devolverFoco.current = comFoco;
    setAberto(false);
  }

  // Aberto: trava a rolagem do fundo, deixa o resto da página inerte (o TalkBack ignora
  // aria-modal), foca o painel e fecha com Esc.
  useEffect(() => {
    if (!aberto) {
      if (devolverFoco.current) botao.current?.focus();
      devolverFoco.current = false;
      return;
    }
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        devolverFoco.current = true;
        setAberto(false);
      }
    };
    document.addEventListener("keydown", aoTeclar);
    const desfazerInerte = painel.current ? tornarFundoInerte(painel.current) : () => {};
    painel.current?.focus();
    return () => {
      desfazerInerte();
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  return (
    <>
      <button
        ref={botao}
        type="button"
        onClick={abrir}
        aria-haspopup="dialog"
        className="argos-botao fixed right-4 bottom-4 z-30 inline-flex min-h-11 items-center gap-2 rounded-[2px] bg-foreground px-4 text-sm font-medium text-background hover:bg-foreground/85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze print:hidden"
      >
        <Olho className="size-5 shrink-0" />
        Pergunte ao Argos
      </button>

      {jaAbriu && (
        <div
          ref={painel}
          role="dialog"
          aria-modal="true"
          aria-labelledby={idTitulo}
          tabIndex={-1}
          className={`argos-painel fixed inset-0 z-50 flex-col gap-3 bg-background p-4 outline-none md:inset-y-0 md:right-0 md:left-auto md:w-[min(28rem,100vw)] md:border-l md:border-border ${aberto ? "flex" : "hidden"}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 id={idTitulo} className="flex items-center gap-2 text-2xl">
                <Olho className="size-6 shrink-0 text-bronze-texto" />
                Argos
              </h2>
              <p className="text-sm text-muted-foreground">
                Respostas prontas com os dados do site. Não sou uma inteligência artificial e não dou opinião.
              </p>
            </div>
            <button
              type="button"
              onClick={() => fechar(true)}
              className="botao-linha shrink-0 px-3"
            >
              Fechar
              <span className="sr-only"> o chat com o Argos</span>
            </button>
          </div>
          <ArgosChat modo="painel" aoNavegar={() => fechar(false)} />
        </div>
      )}
    </>
  );
}
