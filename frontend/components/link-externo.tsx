import type { AnchorHTMLAttributes } from "react";

/** Link que abre em nova aba: avisa leitores de tela e mostra uma seta discreta. Sem "use client". */
export function LinkExterno({
  children,
  rel = "noopener noreferrer",
  ...resto
}: Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "target">) {
  return (
    <a {...resto} target="_blank" rel={rel}>
      {children}
      <span className="sr-only"> (abre em nova aba)</span>
      <svg
        aria-hidden="true"
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="ml-0.5 inline-block size-[0.7em] shrink-0 align-baseline"
      >
        <path d="M4.5 2H2v8h8V7.5M7 2h3v3M10 2 5.5 6.5" />
      </svg>
    </a>
  );
}
