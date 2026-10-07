"use client";

import { useState } from "react";

/** Botão que copia um texto do Pix (chave ou código copia e cola) com um toque. */
export function CopiarPix({ texto, rotulo }: { texto: string; rotulo: string }) {
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
    } catch {
      // Navegador sem permissão de área de transferência: o texto está visível para copiar à mão.
    }
  }

  return (
    <>
      <button type="button" onClick={copiar} className="botao-linha self-start">
        {copiado ? "Copiado" : rotulo}
      </button>
      <span aria-live="polite" className="sr-only">
        {copiado ? "Copiado para a área de transferência." : ""}
      </span>
    </>
  );
}
