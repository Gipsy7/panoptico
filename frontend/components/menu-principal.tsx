"use client";

import Link from "next/link";
import { useRef } from "react";

const ITENS = [
  { href: "/parlamentares", rotulo: "Parlamentares" },
  { href: "/comparar", rotulo: "Comparar" },
  { href: "/sobre-as-fontes", rotulo: "Fontes" },
  { href: "/apoie", rotulo: "Apoie" },
];

/**
 * Menu do topo. No computador, links em linha; no celular, um <details> que abre um painel
 * (funciona sem JavaScript; com JavaScript, fecha ao escolher um link). Não lê a URL atual de
 * propósito: no layout, isso obrigaria a renderizar o cabeçalho a cada pedido.
 */
export function MenuPrincipal() {
  const celular = useRef<HTMLDetailsElement>(null);
  const fechar = () => {
    if (celular.current) celular.current.open = false;
  };

  return (
    <>
      <nav aria-label="Principal" className="hidden items-center gap-6 text-sm md:flex">
        {ITENS.map((i) => (
          <Link key={i.href} href={i.href} className="underline-offset-4 hover:underline">
            {i.rotulo}
          </Link>
        ))}
        <Link href="/#cep" className="botao-linha h-9 px-4">
          Buscar pelo CEP
        </Link>
      </nav>

      <details ref={celular} className="group md:hidden">
        <summary
          aria-label="Menu"
          className="flex size-10 cursor-pointer list-none items-center justify-center rounded-[2px] focus-visible:outline-2 focus-visible:outline-bronze [&::-webkit-details-marker]:hidden"
        >
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M4 7h16M4 12h16M4 17h16" className="group-open:hidden" />
            <path d="M6 6l12 12M18 6L6 18" className="hidden group-open:block" />
          </svg>
        </summary>
        <nav
          aria-label="Principal"
          className="absolute inset-x-0 top-full border-b border-border bg-background px-4 pb-5 shadow-[0_16px_24px_-20px_rgb(0_0_0/0.25)]"
        >
          <ul className="lista-fios flex flex-col text-base">
            {ITENS.map((i) => (
              <li key={i.href}>
                <Link href={i.href} onClick={fechar} className="block py-3">
                  {i.rotulo}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/#cep" onClick={fechar} className="botao mt-4 w-full">
            Buscar pelo CEP
          </Link>
        </nav>
      </details>
    </>
  );
}
