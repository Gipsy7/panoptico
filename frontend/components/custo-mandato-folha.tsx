"use client";

/**
 * Folha "De onde vem cada valor" da seção "Quanto custa o mandato": o ato oficial de cada parcela,
 * a data em que passou a valer e o link. Mesmo padrão da gaveta do dicionário
 * (components/termo-oficial.tsx): sobe de baixo, véu, foco preso, fundo inerte, Esc fecha e
 * devolve o foco ao botão. Sem JavaScript, a lista aparece num <details>.
 */
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";

import { LinkExterno } from "@/components/link-externo";
import type { ItemCustoMandato } from "@/lib/api";
import { formatarData, formatarReais } from "@/lib/formato";
import { tornarFundoInerte } from "@/lib/fundo-inerte";

const nada = () => () => {};

function useNoCliente(): boolean {
  return useSyncExternalStore(
    nada,
    () => true,
    () => false,
  );
}

const ROTULO = "De onde vem cada valor";

export function FolhaAtos({ casaNome, itens }: { casaNome: string; itens: ItemCustoMandato[] }) {
  const noCliente = useNoCliente();
  const [aberta, setAberta] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);

  if (!noCliente) {
    return (
      <details className="rounded-[2px] border border-border p-3">
        <summary className="cursor-pointer text-base font-medium">{ROTULO}</summary>
        <ListaAtos itens={itens} />
      </details>
    );
  }

  return (
    <>
      <button
        ref={botao}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={aberta}
        onClick={() => setAberta(true)}
        className="botao-linha w-full"
      >
        {ROTULO}
      </button>
      {aberta &&
        createPortal(
          <Gaveta
            casaNome={casaNome}
            itens={itens}
            aoFechar={(devolverFoco) => {
              setAberta(false);
              if (devolverFoco) botao.current?.focus();
            }}
          />,
          document.body,
        )}
    </>
  );
}

function Gaveta({
  casaNome,
  itens,
  aoFechar,
}: {
  casaNome: string;
  itens: ItemCustoMandato[];
  aoFechar: (devolverFoco: boolean) => void;
}) {
  const idTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const desfazerInerte = useRef<(() => void) | null>(null);
  const fecharRef = useRef(aoFechar);
  useEffect(() => {
    fecharRef.current = aoFechar;
  });

  function fechar(devolverFoco: boolean) {
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

  return (
    <div ref={caixa} className="gaveta-termo-caixa">
      <div aria-hidden className="gaveta-termo-veu" onClick={() => fechar(true)} />
      <div ref={folha} role="dialog" aria-modal="true" aria-labelledby={idTitulo} tabIndex={-1} className="gaveta-termo">
        <button type="button" onClick={() => fechar(true)} aria-label="Fechar" className="gaveta-termo-fechar">
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <p className="pr-12 text-xs font-medium tracking-[0.12em] text-bronze-texto uppercase">{casaNome}</p>
        <h2 id={idTitulo} className="pr-12 text-3xl leading-tight">
          {ROTULO}
        </h2>
        <p className="mt-[var(--esp-2)] text-sm text-muted-foreground">
          O ato oficial que fixa cada parcela e a data em que passou a valer.
        </p>
        <ListaAtos itens={itens} />
      </div>
    </div>
  );
}

function ListaAtos({ itens }: { itens: ItemCustoMandato[] }) {
  return (
    <ul className="mt-[var(--esp-3)] border-t border-border">
      {itens.map((i) => (
        <li key={i.item} className="flex flex-col gap-1 border-b border-border py-3 text-base">
          <span className="text-sm text-muted-foreground">
            {i.nome} · {i.valor === null ? "valor não publicado" : formatarReais(i.valor)}
          </span>
          <b className="font-medium">{i.ato ?? (i.valor === null ? "Sem ato publicado" : "Valor publicado pela Casa, sem citar o ato")}</b>
          <span className="text-sm text-muted-foreground">
            {i.vigente_desde ? `Vale desde ${formatarData(i.vigente_desde)}` : `Consultado em ${formatarData(i.consultado_em)}`}
          </span>
          {i.observacao && <span className="text-sm text-muted-foreground">{i.observacao}</span>}
          <span className="flex flex-wrap gap-x-4">
            {i.ato_url && (
              <LinkExterno href={i.ato_url} className="alvo-link text-sm underline underline-offset-2">
                Ler o ato
              </LinkExterno>
            )}
            {i.valor_url && i.valor_url !== i.ato_url && (
              <LinkExterno href={i.valor_url} className="alvo-link text-sm underline underline-offset-2">
                Ver o valor na página oficial
              </LinkExterno>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
