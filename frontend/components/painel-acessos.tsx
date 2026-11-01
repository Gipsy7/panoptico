"use client";

/**
 * Painel privado de acessos (docs/DECISOES.md, 2026-10-31). Só cliente: o servidor nunca renderiza
 * dado daqui. O token (12 h) fica no sessionStorage da aba, não em cookie. Só totais agregados.
 */
import { useCallback, useEffect, useId, useSyncExternalStore } from "react";

import { Entrar } from "@/components/painel-acessos-entrar";
import { PainelDados } from "@/components/painel-acessos-dados";
import { CHAVE_SEM_CONTAGEM } from "@/lib/metricas";

const CHAVE_TOKEN = "panoptico-painel-token";

// O token vive só no sessionStorage da aba; este "store" faz o React reler quando ele muda.
const ouvintes = new Set<() => void>();
function lerToken(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_TOKEN);
  } catch {
    return null;
  }
}
function guardarToken(t: string | null) {
  try {
    if (t) sessionStorage.setItem(CHAVE_TOKEN, t);
    else sessionStorage.removeItem(CHAVE_TOKEN);
  } catch {}
  ouvintes.forEach((f) => f());
}
function assinar(f: () => void) {
  ouvintes.add(f);
  return () => void ouvintes.delete(f);
}

export function PainelAcessos() {
  // undefined = ainda no servidor/hidratando (nada é desenhado).
  const token = useSyncExternalStore(assinar, lerToken, () => undefined);
  const pronto = token !== undefined;
  const titulo = useId();

  useEffect(() => {
    try {
      // O aparelho de quem abre o painel deixa de ser contado.
      localStorage.setItem(CHAVE_SEM_CONTAGEM, "1");
    } catch {}
  }, []);

  const sair = useCallback(() => guardarToken(null), []);

  if (!pronto) return null;
  return (
    <div className="pagina-secoes" data-largura="larga">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Área privada</p>
        <h1 id={titulo} className="titulo-pagina">
          Painel de acessos
        </h1>
      </header>
      {token ? <PainelDados token={token} sair={sair} /> : <Entrar aoEntrar={guardarToken} />}
    </div>
  );
}
