/**
 * Peças do padrão de filtros (ver ui/painel-filtros.tsx e docs/DESIGN.md, "Filtros"): campos
 * grandes, pílulas dos filtros ativos (cada uma tira o seu filtro) e o estado vazio. Servem em
 * Server e em Client Components; as versões com `aoRemover`/`aoLimpar` só em Client Components.
 */
import Link from "next/link";

import { cn } from "@/lib/utils";

export type Opcao = { valor: string; rotulo: string };

export function CampoSelect({
  rotulo,
  name,
  opcoes,
  defaultValue,
  ajuda,
  className,
  id,
}: {
  rotulo: string;
  name: string;
  opcoes: Opcao[];
  defaultValue?: string;
  ajuda?: string;
  className?: string;
  id?: string;
}) {
  return (
    <label className={cn("flex min-w-0 flex-col gap-[var(--esp-1)] text-sm font-medium", className)}>
      {rotulo}
      <select id={id} name={name} defaultValue={defaultValue ?? ""} className="campo-filtro font-normal">
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
      {ajuda && <span className="font-normal text-muted-foreground">{ajuda}</span>}
    </label>
  );
}

export function CampoTexto({
  rotulo,
  name,
  defaultValue,
  placeholder,
  className,
}: {
  rotulo: string;
  name: string;
  defaultValue?: string;
  placeholder?: string;
  className?: string;
}) {
  return (
    <label className={cn("flex min-w-0 flex-col gap-[var(--esp-1)] text-sm font-medium", className)}>
      {rotulo}
      <input
        type="search"
        name={name}
        defaultValue={defaultValue}
        placeholder={placeholder}
        enterKeyHint="search"
        className="campo-filtro font-normal"
      />
    </label>
  );
}

export type FiltroAtivo = {
  rotulo: string;
  /** Endereço sem esse filtro (Server Components). */
  href?: string;
  /** Ou a ação que o tira (Client Components). */
  aoRemover?: () => void;
};

const PILULA =
  "inline-flex min-h-11 max-w-full items-center gap-[var(--esp-2)] border border-foreground bg-accent px-[var(--esp-3)] text-left text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze";

/** Filtros ativos como pílulas removíveis (×), que quebram linha em vez de rolar para o lado. */
export function PilulasAtivas({
  itens,
  limparHref,
  aoLimpar,
}: {
  itens: FiltroAtivo[];
  limparHref?: string;
  aoLimpar?: () => void;
}) {
  if (itens.length === 0) return null;
  return (
    <div className="flex flex-col gap-[var(--esp-2)]">
      <p className="text-sm text-muted-foreground">
        {itens.length === 1 ? "Filtro ativo (toque para tirar):" : "Filtros ativos (toque para tirar):"}
      </p>
      <ul className="flex flex-wrap items-center gap-[var(--esp-2)]">
        {itens.map((f) => {
          const conteudo = (
            <>
              <span className="min-w-0 break-words">{f.rotulo}</span>
              <span aria-hidden className="text-base leading-none">
                ×
              </span>
            </>
          );
          return (
            <li key={f.rotulo} className="max-w-full">
              {f.href ? (
                <Link href={f.href} scroll={false} aria-label={`Tirar o filtro ${f.rotulo}`} className={PILULA}>
                  {conteudo}
                </Link>
              ) : (
                <button type="button" onClick={f.aoRemover} aria-label={`Tirar o filtro ${f.rotulo}`} className={PILULA}>
                  {conteudo}
                </button>
              )}
            </li>
          );
        })}
        {itens.length > 1 && (limparHref || aoLimpar) && (
          <li>
            {limparHref ? (
              <Link href={limparHref} scroll={false} className="alvo-link px-[var(--esp-2)] text-sm underline underline-offset-4">
                Limpar tudo
              </Link>
            ) : (
              <button type="button" onClick={aoLimpar} className="alvo-link px-[var(--esp-2)] text-sm underline underline-offset-4">
                Limpar tudo
              </button>
            )}
          </li>
        )}
      </ul>
    </div>
  );
}

/** Lista vazia por causa dos filtros: diz isso e oferece o caminho de volta. */
export function SemResultados({
  mensagem = "Nenhum resultado com esses filtros.",
  limparHref,
  aoLimpar,
  rotuloLimpar = "Limpar os filtros",
  children,
}: {
  mensagem?: string;
  rotuloLimpar?: string;
  limparHref?: string;
  aoLimpar?: () => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-[var(--esp-3)] border-t border-border pt-[var(--esp-4)]">
      <p className="font-medium">{mensagem}</p>
      {children}
      {limparHref ? (
        <Link href={limparHref} scroll={false} className="botao-linha">
          {rotuloLimpar}
        </Link>
      ) : aoLimpar ? (
        <button type="button" onClick={aoLimpar} className="botao-linha">
          {rotuloLimpar}
        </button>
      ) : null}
    </div>
  );
}
