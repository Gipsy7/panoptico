"use client";

/**
 * Termo oficial que se explica ao toque (docs/DESIGN.md, "Dicionário"): sublinhado em pontinhos,
 * com um "?" ao lado. Tocar abre a gaveta que sobe de baixo, com o nome simples, o termo oficial,
 * a explicação, um exemplo do site, a fonte e os botões "Ver no dicionário" e "Perguntar ao Argos".
 * O texto é o mesmo de /dicionario e do Argos (lib/dicionario.ts).
 *
 * Sem JavaScript, o termo é um link para /dicionario#id. A gaveta começa fechada, prende o foco,
 * deixa o resto da página inerte, fecha com Esc, com o "×" ou tocando no véu, e devolve o foco ao
 * termo.
 */
import Link from "next/link";
import { type ReactNode, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";

import { LinkExterno } from "@/components/link-externo";
import { enderecoPergunta, pedirAoArgos } from "@/lib/argos/eventos";
import { DICIONARIO_CONFERIDO_EM, type Termo, termoPorId } from "@/lib/dicionario";
import { formatarData } from "@/lib/formato";
import { tornarFundoInerte } from "@/lib/fundo-inerte";
import { cn } from "@/lib/utils";

const nada = () => () => {};

/** `true` só depois da hidratação (no servidor e no HTML inicial, `false`). */
function useNoCliente(): boolean {
  return useSyncExternalStore(
    nada,
    () => true,
    () => false,
  );
}

export function TermoOficial({
  id,
  children,
  className,
}: {
  /** Id do termo em lib/dicionario.ts. */
  id: string;
  /** Texto que aparece na frase; sem ele, o nome oficial do dicionário. */
  children?: ReactNode;
  className?: string;
}) {
  const termo = termoPorId(id);
  const noCliente = useNoCliente();
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);
  const texto = children ?? termo?.oficial;

  if (!termo) return <>{children}</>;

  const conteudo = (
    <>
      {texto}
      <span aria-hidden className="termo-oficial-icone">
        ?
      </span>
    </>
  );

  if (!noCliente) {
    return (
      <a href={`/dicionario#${termo.id}`} className={cn("termo-oficial", className)}>
        {conteudo}
        <span className="sr-only"> (o que quer dizer)</span>
      </a>
    );
  }

  return (
    <>
      <button
        ref={botao}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={aberto}
        onClick={() => setAberto(true)}
        className={cn("termo-oficial", className)}
      >
        {conteudo}
        <span className="sr-only">: o que quer dizer</span>
      </button>
      {aberto &&
        createPortal(
          <GavetaTermo
            termo={termo}
            aoFechar={(devolverFoco) => {
              setAberto(false);
              if (devolverFoco) botao.current?.focus();
            }}
          />,
          document.body,
        )}
    </>
  );
}

/** Gaveta com a explicação do termo; o pai a desmonta ao fechar. */
function GavetaTermo({ termo, aoFechar }: { termo: Termo; aoFechar: (devolverFoco: boolean) => void }) {
  const idTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const desfazerInerte = useRef<(() => void) | null>(null);
  const fecharRef = useRef(aoFechar);
  useEffect(() => {
    fecharRef.current = aoFechar;
  });

  function fechar(devolverFoco: boolean) {
    // Tira o inert antes de devolver o foco (um botão inerte não recebe foco).
    desfazerInerte.current?.();
    desfazerInerte.current = null;
    fecharRef.current(devolverFoco);
  }

  useEffect(() => {
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (caixa.current) desfazerInerte.current = tornarFundoInerte(caixa.current);
    folha.current?.focus();
    const focaveis = () =>
      [...(folha.current?.querySelectorAll<HTMLElement>("a[href], button") ?? [])].filter((e) => e.offsetParent !== null);
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        desfazerInerte.current?.();
        desfazerInerte.current = null;
        fecharRef.current(true);
      } else if (e.key === "Tab") {
        const lista = focaveis();
        if (!lista.length) return;
        const [primeiro, ultimo] = [lista[0], lista[lista.length - 1]];
        const atual = document.activeElement;
        if (e.shiftKey && (atual === primeiro || atual === folha.current)) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && atual === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    };
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
      desfazerInerte.current?.();
      desfazerInerte.current = null;
    };
  }, []);

  const pergunta = `o que é ${termo.termo.toLowerCase()}?`;

  return (
    <div ref={caixa} className="gaveta-termo-caixa">
      <div aria-hidden className="gaveta-termo-veu" onClick={() => fechar(true)} />
      <div
        ref={folha}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        className="gaveta-termo"
      >
        <button type="button" onClick={() => fechar(true)} aria-label="Fechar a explicação" className="gaveta-termo-fechar">
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <Explicacao termo={termo} idTitulo={idTitulo} nivel="h2" aoNavegar={() => fechar(false)} />
        <div className="mt-[var(--esp-3)] grid grid-cols-1 gap-[var(--esp-2)] min-[22rem]:grid-cols-2">
          <Link href={`/dicionario#${termo.id}`} onClick={() => fechar(false)} className="botao-linha w-full">
            Ver no dicionário
          </Link>
          <a
            href={enderecoPergunta(pergunta)}
            onClick={(e) => {
              fechar(false);
              if (pedirAoArgos(pergunta)) e.preventDefault();
            }}
            className="botao-linha w-full"
          >
            Perguntar ao Argos
          </a>
        </div>
      </div>
    </div>
  );
}

/**
 * Corpo da explicação: o mesmo na gaveta e no índice /dicionario. Sem estado (serve no servidor e
 * no cliente).
 */
export function Explicacao({
  termo,
  idTitulo,
  nivel = "h2",
  aoNavegar,
  semTitulo = false,
}: {
  termo: Termo;
  idTitulo?: string;
  nivel?: "h2" | "h3";
  aoNavegar?: () => void;
  semTitulo?: boolean;
}) {
  const Titulo = nivel;
  return (
    <div className="explicacao-termo">
      {!semTitulo && (
        <>
          <Titulo id={idTitulo} className="pr-12 text-3xl leading-tight">
            {termo.termo}
          </Titulo>
          <p className="pr-12 text-sm text-muted-foreground">Termo oficial: {termo.oficial}</p>
        </>
      )}
      <p className="mt-[var(--esp-3)] text-base leading-relaxed">{termo.explicacao}</p>
      {termo.exemplo && (
        <p className="explicacao-termo-exemplo">
          <span className="block text-xs font-medium tracking-[0.12em] text-bronze-texto uppercase">No Panóptico</span>
          <Link href={termo.exemplo.href} onClick={aoNavegar} className="alvo-link underline underline-offset-4">
            {termo.exemplo.rotulo}
          </Link>
        </p>
      )}
      <p className="mt-[var(--esp-3)] text-sm text-muted-foreground">
        Fonte:{" "}
        <LinkExterno href={termo.fonte.url} className="underline underline-offset-2">
          {termo.fonte.rotulo}
        </LinkExterno>{" "}
        · conferido em {formatarData(DICIONARIO_CONFERIDO_EM)}
      </p>
    </div>
  );
}
