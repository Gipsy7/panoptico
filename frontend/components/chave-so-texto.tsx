"use client";

/**
 * Chave liga/desliga "Só o que muda leis" (Frente 4, escolha A do dono): esconde as votações de
 * procedimento (urgência, adiamento, retirada de pauta...). É um link com papel de chave: sem
 * JavaScript funciona como link; com JavaScript, Espaço também liga e desliga (como um botão) e
 * a página troca sem voltar ao topo. O aviso do que ficou de fora fica logo abaixo, em quem chama.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { cn } from "@/lib/utils";

export function ChaveSoTexto({
  ligada,
  href,
  className,
}: {
  ligada: boolean;
  /** Endereço com a chave no estado oposto ao atual. */
  href: string;
  className?: string;
}) {
  const router = useRouter();
  const [trocando, iniciar] = useTransition();
  return (
    <Link
      href={href}
      scroll={false}
      role="switch"
      aria-checked={ligada}
      aria-busy={trocando || undefined}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        iniciar(() => router.push(href, { scroll: false }));
      }}
      onKeyDown={(e) => {
        if (e.key === " ") {
          e.preventDefault();
          iniciar(() => router.push(href, { scroll: false }));
        }
      }}
      className={cn(
        "flex min-h-11 items-center justify-between gap-3 rounded-xl bg-card p-3 ring-1 ring-foreground/10",
        "hover:bg-accent/50",
        className,
      )}
    >
      <span className="flex min-w-0 flex-col">
        <span className="font-semibold">Só o que muda leis</span>
        <span className="text-sm text-muted-foreground">
          Esconde pedidos de urgência, adiamento e outros procedimentos
        </span>
      </span>
      <span
        aria-hidden
        className={cn(
          "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border-2 transition-colors",
          ligada ? "border-foreground bg-foreground" : "border-muted-foreground bg-transparent",
        )}
      >
        <span
          className={cn(
            "absolute size-5 rounded-full transition-[left]",
            ligada ? "left-[1.375rem] bg-background" : "left-0.5 bg-muted-foreground",
          )}
        />
      </span>
    </Link>
  );
}
