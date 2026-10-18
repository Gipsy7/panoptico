/**
 * Lista com fios que mostra só os primeiros itens; o restante fica num <details> ("Ver todos
 * os N"). Servidor, sem JS. Sem `limite` (ou com lista curta), mostra tudo.
 *
 * Uso:
 *   <ListaResumida limite={8} rotulo="Ver todos os 70" itens={deputados.map((d) => <li key=…>…</li>)} />
 * Cada item já vem como <li> com `border-b border-border`.
 */
import type { ReactNode } from "react";

const CLASSE_UL = "grid border-t border-border sm:grid-cols-2 sm:gap-x-10";

export function ListaResumida({
  itens,
  limite,
  total,
}: {
  itens: ReactNode[];
  limite?: number;
  /** Total para o rótulo; padrão = tamanho da lista. */
  total?: number;
}) {
  if (!limite || itens.length <= limite + 1) return <ul className={CLASSE_UL}>{itens}</ul>;
  const resto = itens.slice(limite);
  return (
    <div className="flex flex-col gap-3">
      <ul className={CLASSE_UL}>{itens.slice(0, limite)}</ul>
      <details className="painel">
        <summary className="flex min-h-11 cursor-pointer items-center font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
          Ver todos os {(total ?? itens.length).toLocaleString("pt-BR")} (mais {resto.length})
        </summary>
        <ul className={`${CLASSE_UL} mt-3`}>{resto}</ul>
      </details>
    </div>
  );
}
