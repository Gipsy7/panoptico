"use client";

import { useState } from "react";

/** Mostra a chave Pix e copia com um toque. Sem JavaScript, a chave continua selecionável. */
export function CopiarPix({ chave }: { chave: string }) {
  const [copiada, setCopiada] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(chave);
      setCopiada(true);
      setTimeout(() => setCopiada(false), 2500);
    } catch {
      // Navegador sem permissão de área de transferência: a chave está visível para copiar à mão.
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="numero text-base break-all select-all sm:text-lg">{chave}</p>
      <button type="button" onClick={copiar} className="botao-linha self-start">
        {copiada ? "Chave copiada" : "Copiar chave Pix"}
      </button>
      <p aria-live="polite" className="sr-only">
        {copiada ? "Chave Pix copiada para a área de transferência." : ""}
      </p>
    </div>
  );
}
