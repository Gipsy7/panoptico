"use client";

/**
 * "Ver o resultado desta eleição" na carreira (versão A, Frente 5): abre uma gaveta de baixo
 * com a tabela da eleição daquela candidatura, no mesmo padrão da gaveta do dicionário (foco
 * preso, fundo inerte, Esc fecha e devolve o foco ao botão).
 */
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { TabelaResultado } from "@/components/eleicao/tabela-resultado";
import { type ResultadoEleicao, urlResultadoEleicao } from "@/lib/api";
import { tornarFundoInerte } from "@/lib/fundo-inerte";

type Estado =
  | { tipo: "carregando" }
  | { tipo: "ok"; r: ResultadoEleicao }
  | { tipo: "falta" }
  | { tipo: "erro" };

export function GavetaResultado({
  candidaturaId,
  rotulo,
}: {
  candidaturaId: number;
  rotulo: string;
}) {
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button
        ref={botao}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={aberto}
        onClick={() => setAberto(true)}
        className="botao-linha self-start"
      >
        Ver o resultado desta eleição
        <span className="sr-only"> ({rotulo})</span>
      </button>
      {aberto &&
        createPortal(
          <Gaveta
            candidaturaId={candidaturaId}
            aoFechar={(devolver) => {
              setAberto(false);
              if (devolver) botao.current?.focus();
            }}
          />,
          document.body,
        )}
    </>
  );
}

function Gaveta({
  candidaturaId,
  aoFechar,
}: {
  candidaturaId: number;
  aoFechar: (devolver: boolean) => void;
}) {
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const caixa = useRef<HTMLDivElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const fecharRef = useRef(aoFechar);
  useEffect(() => {
    fecharRef.current = aoFechar;
  });

  useEffect(() => {
    let vivo = true;
    fetch(urlResultadoEleicao(candidaturaId))
      .then(async (resp) => {
        if (!vivo) return;
        if (resp.status === 404) return setEstado({ tipo: "falta" });
        if (!resp.ok) return setEstado({ tipo: "erro" });
        setEstado({ tipo: "ok", r: (await resp.json()) as ResultadoEleicao });
      })
      .catch(() => vivo && setEstado({ tipo: "erro" }));
    return () => {
      vivo = false;
    };
  }, [candidaturaId]);

  useEffect(() => {
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const desfazer = caixa.current ? tornarFundoInerte(caixa.current) : null;
    folha.current?.focus();
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        desfazer?.();
        fecharRef.current(true);
      } else if (e.key === "Tab") {
        const lista = [
          ...(folha.current?.querySelectorAll<HTMLElement>(
            "a[href], button, summary",
          ) ?? []),
        ].filter((el) => el.offsetParent !== null);
        if (!lista.length) return;
        const [primeiro, ultimo] = [lista[0], lista[lista.length - 1]];
        if (
          e.shiftKey &&
          (document.activeElement === primeiro ||
            document.activeElement === folha.current)
        ) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    };
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
      desfazer?.();
    };
  }, []);

  return (
    <div ref={caixa} className="gaveta-termo-caixa">
      <div
        aria-hidden
        className="gaveta-termo-veu"
        onClick={() => fecharRef.current(true)}
      />
      <div
        ref={folha}
        role="dialog"
        aria-modal="true"
        aria-label="Resultado da eleição"
        tabIndex={-1}
        className="gaveta-termo"
      >
        <button
          type="button"
          onClick={() => fecharRef.current(true)}
          aria-label="Fechar o resultado"
          className="gaveta-termo-fechar"
        >
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            className="size-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          >
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <div role="status" aria-live="polite" className="pr-10">
          {estado.tipo === "carregando" && (
            <p className="text-sm text-muted-foreground">
              Carregando o resultado…
            </p>
          )}
          {estado.tipo === "falta" && (
            <p className="text-sm">
              O resultado completo desta eleição ainda não está no Panóptico.
              Hoje temos de 2016 a 2026.
            </p>
          )}
          {estado.tipo === "erro" && (
            <p className="text-sm">
              Não deu para carregar o resultado agora. Tente de novo em
              instantes.
            </p>
          )}
        </div>
        {estado.tipo === "ok" && <TabelaResultado r={estado.r} />}
      </div>
    </div>
  );
}
