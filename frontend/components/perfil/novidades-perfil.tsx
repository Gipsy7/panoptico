"use client";

/**
 * "Desde a sua última visita": guarda neste aparelho (localStorage, com try/catch) a data e os
 * valores dos cartões e, na volta, marca os que mudaram. Nada vai ao servidor. Na primeira visita
 * não mostra nada. Segue o modelo de uf-escolhida.tsx (lê depois da hidratação, sem quebrar se o
 * armazenamento estiver bloqueado).
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { chaveVisita, compararVisita, hojeISO, lerVisita, type Novidades, type Valores } from "@/lib/novidades-perfil";

const NovidadesContexto = createContext<Novidades | null>(null);

export function NovidadesProvider({ valores, children }: { valores: Valores; children: ReactNode }) {
  const [novidades, setNovidades] = useState<Novidades | null>(null);
  const assinatura = JSON.stringify(valores);

  useEffect(() => {
    const atuais = JSON.parse(assinatura) as Valores;
    const quadro = requestAnimationFrame(() => {
      try {
        const chave = chaveVisita(window.location.pathname);
        const anterior = lerVisita(window.localStorage.getItem(chave));
        setNovidades(compararVisita(anterior, atuais));
        // Guarda a visita de agora; sem mudança, mantém a data de antes (a base da comparação).
        const mudou = !anterior || JSON.stringify(anterior.valores) !== JSON.stringify(atuais);
        if (mudou) window.localStorage.setItem(chave, JSON.stringify({ data: hojeISO(), valores: atuais }));
      } catch {
        // Armazenamento bloqueado: a página funciona igual, sem lembrar.
      }
    });
    return () => cancelAnimationFrame(quadro);
  }, [assinatura]);

  return <NovidadesContexto.Provider value={novidades}>{children}</NovidadesContexto.Provider>;
}

/** Pontinho "novo" dentro do cartão cujo valor mudou; fora do provider ou sem mudança, não aparece. */
export function PontinhoNovo({ destino }: { destino: string }) {
  const n = useContext(NovidadesContexto);
  if (!n || !n.cartoes.includes(destino)) return null;
  return (
    <span className="inline-flex items-center gap-1 self-start text-xs font-semibold uppercase tracking-wide text-bronze-texto">
      <i aria-hidden className="size-2 rounded-full bg-bronze" />
      novo<span className="sr-only">: mudou desde {n.desde}</span>
    </span>
  );
}

/** Linha curta acima das frases ("Desde 12/10: 4 votações a mais") e a explicação do pontinho. */
export function LinhaNovidades() {
  const n = useContext(NovidadesContexto);
  return (
    <>
      {n && (
        <p className="text-sm">
          <span className="font-medium">Desde {n.desde}:</span>{" "}
          {n.linha ?? "alguns números mudaram (marcados com o pontinho)"}.
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        {n && (
          <>
            O pontinho <i aria-hidden className="inline-block size-2 rounded-full bg-bronze align-baseline" /> marca o
            número que mudou desde a sua última visita.{" "}
          </>
        )}
        Guardado só neste aparelho: o Panóptico não recebe nem guarda a sua visita.
      </p>
    </>
  );
}
