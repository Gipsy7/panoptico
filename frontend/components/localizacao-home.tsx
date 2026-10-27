"use client";

import { type ReactNode, createContext, useContext, useMemo, useState } from "react";

import type { CidadeAchada } from "@/lib/localizacao";

// Cidade que o aparelho achou, compartilhada só na home entre o formulário, o exemplo de
// comparação e as curiosidades. Vive em memória (estado do React): não vai a cookie, URL nem
// armazenamento, e some ao sair da página.
type Valor = { cidade: CidadeAchada | null; definirCidade: (c: CidadeAchada | null) => void };

const Contexto = createContext<Valor>({ cidade: null, definirCidade: () => {} });

export function LocalizacaoProvider({ children }: { children: ReactNode }) {
  const [cidade, definirCidade] = useState<CidadeAchada | null>(null);
  const valor = useMemo(() => ({ cidade, definirCidade }), [cidade]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useCidadeAchada(): Valor {
  return useContext(Contexto);
}
