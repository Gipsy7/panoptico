"use client";

import { useEffect, useRef } from "react";

import { registrarBusca } from "@/components/contagem-acessos";
import type { FormaDeBusca } from "@/lib/metricas";

/**
 * Conta uma busca de representantes depois que o resultado existe (docs/DECISOES.md,
 * 2026-10-31). Recebe só a forma da busca, se houve resultado e, quando houve, a UF e o código
 * IBGE da cidade que o resultado devolveu. Nunca recebe o CEP. Não desenha nada.
 */
export function RegistrarBusca({
  forma,
  resultado,
  uf,
  ibge,
}: {
  forma: FormaDeBusca;
  resultado: boolean;
  uf?: string | null;
  ibge?: string | null;
}) {
  const feito = useRef(false);
  useEffect(() => {
    if (feito.current) return; // o modo estrito do React roda o efeito duas vezes
    feito.current = true;
    registrarBusca(forma, resultado, uf, ibge);
  }, [forma, resultado, uf, ibge]);
  return null;
}
