"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { AlternarTema } from "@/components/alternar-tema";
import { tornarFundoInerte } from "@/lib/fundo-inerte";

const ITENS = [
  { href: "/parlamentares", rotulo: "Parlamentares" },
  { href: "/projetos", rotulo: "Projetos e votações" },
  { href: "/comparar", rotulo: "Comparar" },
  { href: "/impostos-e-repasses", rotulo: "Impostos e repasses" },
  { href: "/partidos", rotulo: "Partidos" },
  { href: "/apoie", rotulo: "Apoie" },
];

/**
 * Menu do topo. No computador, links em linha. No celular, o botão "Buscar pelo CEP" fica sempre
 * visível e o menu é um botão (`aria-expanded`) que abre um painel sob o cabeçalho; o painel fecha
 * ao tocar num link, ao tocar fora e com Esc, e trava a rolagem do fundo. Não lê a URL atual de
 * propósito: no layout, isso obrigaria a renderizar o cabeçalho a cada pedido. O botão de tema
 * (só o ícone de sol/lua) fica no cabeçalho; em telas abaixo de 640 px, no topo do painel do menu.
 */
export function MenuPrincipal() {
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);
  const painel = useRef<HTMLDivElement>(null);

  function aoSairFoco(e: React.FocusEvent<HTMLDivElement>) {
    const para = e.relatedTarget as Node | null;
    if (!para || e.currentTarget.contains(para) || botao.current?.contains(para)) return;
    setAberto(false);
  }

  useEffect(() => {
    if (!aberto) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAberto(false);
        botao.current?.focus();
      }
    };
    document.addEventListener("keydown", aoTeclar);
    // Resto da página inerte (o TalkBack ignora aria-modal); o botão do menu continua ativo.
    const desfazerInerte = painel.current ? tornarFundoInerte(painel.current, [botao.current]) : () => {};
    return () => {
      desfazerInerte();
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  return (
    <>
      <nav aria-label="Principal" className="hidden items-center gap-3 text-sm whitespace-nowrap xl:flex xl:gap-6">
        {ITENS.map((i) => (
          <Link key={i.href} href={i.href} className="alvo-link underline-offset-4 hover:underline">
            {i.rotulo}
          </Link>
        ))}
        <Link href="/#cep" className="botao-linha px-4 whitespace-nowrap">
          Buscar pelo CEP
        </Link>
        <AlternarTema />
      </nav>

      <div className="flex items-center gap-2 xl:hidden">
        {/* Botão de tema no cabeçalho quando cabe (a partir de 640 px); abaixo disso, no topo do menu. */}
        <div className="hidden sm:block">
          <AlternarTema />
        </div>
        <Link href="/#cep" onClick={() => setAberto(false)} aria-label="Buscar seus representantes" className="botao-linha px-3 whitespace-nowrap">
          Buscar
        </Link>
        <button
          ref={botao}
          type="button"
          aria-label={aberto ? "Fechar o menu" : "Abrir o menu"}
          aria-expanded={aberto}
          aria-controls="menu-celular"
          onClick={() => setAberto((v) => !v)}
          className="flex size-11 items-center justify-center rounded-[2px] focus-visible:outline-2 focus-visible:outline-bronze"
        >
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            {aberto ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </div>

      {aberto && (
        // O painel fecha quando o foco sai dele (exceto para o botão do menu, que alterna).
        // eslint-disable-next-line jsx-a11y/no-static-element-interactions -- só observa a saída do foco; não recebe clique nem tecla
        <div
          id="menu-celular"
          ref={painel}
          onBlur={aoSairFoco}
          className="absolute inset-x-0 top-full h-[calc(100dvh-3.5rem)] bg-background/95 xl:hidden"
        >
          {/* Fundo: botão transparente que fecha ao toque fora da lista. Fora da ordem de Tab e
              do leitor de tela de propósito: o botão do menu (sempre visível) já fecha. */}
          <button
            type="button"
            tabIndex={-1}
            aria-hidden
            aria-label="Fechar o menu"
            onClick={() => setAberto(false)}
            className="absolute inset-0 size-full cursor-default"
          />
          <nav aria-label="Menu" className="relative border-b border-border bg-background px-4 pb-5 shadow-[var(--sombra-menu)]">
            <div className="flex justify-end pt-1 sm:hidden">
              <AlternarTema />
            </div>
            <ul className="lista-fios flex flex-col text-base">
              {ITENS.map((i) => (
                <li key={i.href}>
                  <Link href={i.href} onClick={() => setAberto(false)} className="flex min-h-12 items-center">
                    {i.rotulo}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      )}
    </>
  );
}
