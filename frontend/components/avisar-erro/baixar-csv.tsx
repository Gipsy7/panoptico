"use client";

import { type Correcao, correcoesParaCsv } from "@/lib/correcoes";

/** Baixa a tabela de correções em CSV (gerado no navegador, com os mesmos dados da tela). */
export function BaixarCsv({ itens }: { itens: Correcao[] }) {
  function baixar() {
    const blob = new Blob(["﻿", correcoesParaCsv(itens)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "panoptico-correcoes.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }
  return (
    <button type="button" onClick={baixar} className="botao-linha self-start">
      Baixar em CSV
    </button>
  );
}
