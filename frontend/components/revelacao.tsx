import { type ReactNode, Suspense, ViewTransition } from "react";

/**
 * Suspense com transição: enquanto carrega, mostra o esqueleto; quando os dados chegam,
 * o esqueleto sai rápido (desce e some) e o conteúdo entra com calma (sobe e aparece).
 * As animações (.descer/.subir) ficam em globals.css e respeitam "reduzir movimento".
 */
export function Revelacao({ fallback, children }: { fallback: ReactNode; children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <ViewTransition exit="descer" default="none">
          {fallback}
        </ViewTransition>
      }
    >
      <ViewTransition enter="subir" default="none">
        {children}
      </ViewTransition>
    </Suspense>
  );
}
