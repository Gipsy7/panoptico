"use client";

/**
 * "Do meu estado": o estado escolhido vem do endereço (`?uf=SP`, vale para quem abre o link) e,
 * sem ele, do que o aparelho lembrou da última vez (localStorage, com try/catch: pode estar
 * bloqueado). Ao escolher, grava no aparelho e atualiza o endereço sem recarregar a página.
 */
import { useCallback, useEffect, useState } from "react";

import { CHAVE_UF_LEMBRADA, lerUf } from "@/lib/projetos";
import { UFS } from "@/lib/ufs";

export function useUfEscolhida(inicial: string | null) {
  const [uf, setUf] = useState<string | null>(inicial);

  // Sem `?uf=`, usa o estado lembrado neste aparelho.
  useEffect(() => {
    if (inicial) return;
    const quadro = requestAnimationFrame(() => {
      try {
        const lembrada = lerUf(window.localStorage.getItem(CHAVE_UF_LEMBRADA));
        if (lembrada) setUf(lembrada);
      } catch {
        // Armazenamento bloqueado: a página funciona igual, sem lembrar.
      }
    });
    return () => cancelAnimationFrame(quadro);
  }, [inicial]);

  const escolher = useCallback((novo: string | null) => {
    setUf(novo);
    try {
      if (novo) window.localStorage.setItem(CHAVE_UF_LEMBRADA, novo);
      else window.localStorage.removeItem(CHAVE_UF_LEMBRADA);
    } catch {
      // Sem armazenamento: só não lembra.
    }
    try {
      const url = new URL(window.location.href);
      if (novo) url.searchParams.set("uf", novo);
      else url.searchParams.delete("uf");
      window.history.replaceState(window.history.state, "", url);
    } catch {
      // Sem history: o filtro vale só nesta visita.
    }
  }, []);

  return [uf, escolher] as const;
}

export function SeletorUf({
  id,
  uf,
  onChange,
  rotulo = "Ver só o meu estado",
}: {
  id: string;
  uf: string | null;
  onChange: (uf: string | null) => void;
  rotulo?: string;
}) {
  return (
    <label htmlFor={id} className="flex min-w-0 flex-col gap-1 text-sm">
      {rotulo}
      <select
        id={id}
        value={uf ?? ""}
        onChange={(e) => onChange(lerUf(e.target.value))}
        className="seletor w-full sm:w-64"
      >
        <option value="">Todos os estados</option>
        {UFS.map((u) => (
          <option key={u.sigla} value={u.sigla}>
            {u.nome}
          </option>
        ))}
      </select>
    </label>
  );
}
