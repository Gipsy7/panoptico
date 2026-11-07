"use client";

/**
 * Avisar erro / direito de resposta (Frente 7). O perfil se embrulha em `<AvisarErroProvider>`:
 * ele guarda de quem é o perfil, mantém a gaveta (uma só para a página inteira) e deixa as
 * entradas ("Achou um erro neste número?", o botão do checklist, o fim do perfil) abri-la.
 * Fora de um perfil, as entradas não aparecem.
 */
import { usePathname } from "next/navigation";
import { type ReactNode, createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { GavetaAvisar } from "@/components/avisar-erro/gaveta";
import { type PerfilTipo, type TipoAviso, normalizarSecao } from "@/lib/avisar-erro";

export type PerfilAviso = { tipo: PerfilTipo; id: string; nome: string };

type Pedido = { modo: TipoAviso; secao: string | null };

type Contexto = {
  perfil: PerfilAviso;
  /** Seções (já normalizadas) que têm resposta publicada. */
  secoesComResposta: ReadonlySet<string>;
  abrir: (pedido: Pedido, origem: HTMLElement | null) => void;
};

const AvisarErroContexto = createContext<Contexto | null>(null);

/** `null` fora de um perfil. */
export function useAvisarErro(): Contexto | null {
  return useContext(AvisarErroContexto);
}

export function AvisarErroProvider({
  perfil,
  secoesComResposta = [],
  children,
}: {
  perfil: PerfilAviso;
  /** Seções a que as respostas publicadas se referem (texto como foi enviado). */
  secoesComResposta?: string[];
  children: ReactNode;
}) {
  const caminho = usePathname();
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const origem = useRef<HTMLElement | null>(null);
  // Chave que muda a cada abertura: a gaveta começa do zero.
  const [versao, setVersao] = useState(0);

  const abrir = useCallback((p: Pedido, o: HTMLElement | null) => {
    origem.current = o;
    setVersao((v) => v + 1);
    setPedido(p);
  }, []);

  const conjunto = useMemo(() => new Set(secoesComResposta.map(normalizarSecao)), [secoesComResposta]);
  const valor = useMemo(() => ({ perfil, secoesComResposta: conjunto, abrir }), [perfil, conjunto, abrir]);

  return (
    <AvisarErroContexto.Provider value={valor}>
      {children}
      {pedido &&
        createPortal(
          <GavetaAvisar
            key={versao}
            modoInicial={pedido.modo}
            secaoInicial={pedido.secao}
            perfil={perfil}
            pagina={caminho}
            aoFechar={(devolverFoco) => {
              setPedido(null);
              if (devolverFoco) origem.current?.focus();
            }}
          />,
          document.body,
        )}
    </AvisarErroContexto.Provider>
  );
}
