"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const ITENS = [
  { href: "/parlamentares", rotulo: "Parlamentares" },
  { href: "/comparar", rotulo: "Comparar" },
  { href: "/partidos", rotulo: "Partidos" },
  { href: "/sobre-as-fontes", rotulo: "Fontes" },
  { href: "/apoie", rotulo: "Apoie" },
];

/**
 * Menu do topo. No computador, links em linha. No celular, o botão "Buscar pelo CEP" fica sempre
 * visível e o menu é um botão (`aria-expanded`) que abre um painel sob o cabeçalho; o painel fecha
 * ao tocar num link, ao tocar fora e com Esc, e trava a rolagem do fundo. Não lê a URL atual de
 * propósito: no layout, isso obrigaria a renderizar o cabeçalho a cada pedido.
 */
export function MenuPrincipal() {
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);

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
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  return (
    <>
      <nav aria-label="Principal" className="hidden items-center gap-6 text-sm md:flex">
        {ITENS.map((i) => (
          <Link key={i.href} href={i.href} className="alvo-link underline-offset-4 hover:underline">
            {i.rotulo}
          </Link>
        ))}
        <Link href="/#cep" className="botao-linha px-4">
          Buscar pelo CEP
        </Link>
      </nav>

      <div className="flex items-center gap-2 md:hidden">
        <Link href="/#cep" onClick={() => setAberto(false)} aria-label="Buscar pelo CEP" className="botao-linha px-3 whitespace-nowrap">
          Buscar CEP
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
        // Toque fora da lista (na área abaixo dela) fecha o painel.
        <div
          id="menu-celular"
          onClick={() => setAberto(false)}
          className="absolute inset-x-0 top-full h-[calc(100dvh-3.5rem)] bg-background/95 md:hidden"
        >
          <nav
            aria-label="Menu"
            onClick={(e) => e.stopPropagation()}
            className="border-b border-border bg-background px-4 pb-5 shadow-[0_16px_24px_-20px_rgb(0_0_0/0.25)]"
          >
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
