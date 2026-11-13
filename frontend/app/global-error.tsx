"use client";

import "./globals.css";

/** Falha no próprio layout: substitui a página inteira, então traz o seu <html>. */
export default function ErroGeral({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-full flex-col">
        <title>Esta página não abriu · Panóptico</title>
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-3 px-4 py-8">
          <div role="alert" className="painel flex flex-col gap-3">
            <h1 className="text-lg font-semibold">O site não abriu</h1>
            <p className="text-muted-foreground">
              Algo deu errado do nosso lado. Tente de novo em instantes.
            </p>
            <button type="button" onClick={reset} className="botao self-start">
              Tentar de novo
            </button>
            {/* Recarrega tudo de propósito: o layout é o que falhou. */}
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a href="/" className="alvo-link font-medium underline underline-offset-4">
              Voltar para o início
            </a>
          </div>
        </main>
      </body>
    </html>
  );
}
