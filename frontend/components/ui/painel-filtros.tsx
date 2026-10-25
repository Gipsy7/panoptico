"use client";

/**
 * Padrão único de filtros do site (ver docs/DESIGN.md, "Filtros").
 *
 * - Celular: um botão "Filtrar" que diz quantos filtros estão ativos e abre uma folha que sobe de
 *   baixo, com os campos grandes, "Aplicar" e "Limpar". Fecha com Esc, com o "×" ou tocando fora,
 *   trava a rolagem do fundo e devolve o foco ao botão.
 * - Computador (md em diante): os mesmos campos ficam à vista, numa grade.
 * - Sem JavaScript: é um formulário GET comum, sempre aberto (o script do <head> marca
 *   `data-js` na raiz; só com ele a folha se esconde).
 *
 * O estado vive na URL: aplicar navega para o endereço com os campos preenchidos (sem os vazios
 * e sem os que estão no padrão), então o link é compartilhável e o "voltar" funciona. A página
 * deve passar `key` com a consulta atual, para os campos voltarem ao que está na URL depois de
 * navegar (voltar do navegador, tirar uma pílula).
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, useTransition } from "react";

import { tornarFundoInerte } from "@/lib/fundo-inerte";
import { consultaDosCampos, enderecoComConsulta, textoAtivos, type Padroes } from "@/lib/filtros";
import { cn } from "@/lib/utils";

export function PainelFiltros({
  action,
  ancora,
  ativos,
  limparHref,
  padroes,
  ocultos,
  titulo = "Filtrar a lista",
  sempreVisivel = false,
  rotuloAplicar = "Aplicar",
  children,
}: {
  /** Caminho da página (o formulário sem JavaScript envia para cá). */
  action: string;
  /** Âncora da seção, para voltar a ela depois de aplicar (filtros dentro de um perfil). */
  ancora?: string;
  /** Quantos filtros estão ativos agora (mostrado no botão). */
  ativos: number;
  /** Endereço sem nenhum filtro. */
  limparHref: string;
  /** Valores que são o padrão e não precisam ir para a URL. */
  padroes?: Padroes;
  /** Campos que acompanham o formulário sem aparecer (ex.: a busca por texto). */
  ocultos?: Record<string, string | undefined>;
  titulo?: string;
  /** Poucos campos (2 ou 3): sem botão nem folha, os campos ficam sempre à vista. */
  sempreVisivel?: boolean;
  rotuloAplicar?: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [aberto, setAberto] = useState(false);
  const [aplicando, iniciar] = useTransition();
  const botao = useRef<HTMLButtonElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const fundo = useRef<HTMLDivElement>(null);
  const desfazerInerte = useRef<(() => void) | null>(null);
  const idFolha = useId();
  const idTitulo = useId();
  const descricao = textoAtivos(ativos);
  const actionComAncora = enderecoComConsulta(action, "", ancora);

  // Folha aberta (só existe no celular): trava o fundo, Esc fecha, Tab não sai da folha.
  useEffect(() => {
    if (!aberto) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    // O resto da página fica inerte (o TalkBack ignora aria-modal). No computador a folha não é
    // diálogo (os campos ficam à vista), então só se aplica enquanto a largura é de celular.
    if (folha.current && !window.matchMedia("(min-width: 48rem)").matches) {
      desfazerInerte.current = tornarFundoInerte(folha.current, [fundo.current]);
    }
    const focaveis = () =>
      [...(folha.current?.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea") ?? [])].filter(
        (e) => !e.hasAttribute("disabled") && e.getAttribute("type") !== "hidden" && e.offsetParent !== null,
      );
    focaveis()[0]?.focus();
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        fechar();
      } else if (e.key === "Tab") {
        const lista = focaveis();
        if (!lista.length) return;
        const [primeiro, ultimo] = [lista[0], lista[lista.length - 1]];
        if (e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    };
    // Passou para a largura de computador com a folha aberta: os campos já ficam à vista.
    const largura = window.matchMedia("(min-width: 48rem)");
    const aoMudarLargura = () => largura.matches && setAberto(false);
    document.addEventListener("keydown", aoTeclar);
    largura.addEventListener("change", aoMudarLargura);
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
      largura.removeEventListener("change", aoMudarLargura);
      desfazerInerte.current?.();
      desfazerInerte.current = null;
    };
  }, [aberto]);

  function fechar() {
    // Tira o inert antes de devolver o foco (um botão inerte não recebe foco).
    desfazerInerte.current?.();
    setAberto(false);
    botao.current?.focus();
  }

  function aplicar(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const consulta = consultaDosCampos(new FormData(e.currentTarget).entries(), padroes);
    const destino = enderecoComConsulta(action, consulta, ancora);
    setAberto(false);
    iniciar(() => router.push(destino, { scroll: false }));
  }

  const folhaAberta = aberto && !sempreVisivel;

  return (
    <div className="flex flex-col gap-[var(--esp-3)]" data-aplicando={aplicando || undefined}>
      {!sempreVisivel && (
        <button
          ref={botao}
          type="button"
          aria-expanded={aberto}
          aria-controls={idFolha}
          onClick={() => setAberto(true)}
          className={cn(
            // Só aparece no celular e com JavaScript; sem ele, o formulário já está aberto.
            "hidden [:root[data-js]_&]:inline-flex md:[:root[data-js]_&]:hidden",
            "botao-linha h-12 w-full justify-between px-[var(--esp-4)] text-base",
            ativos > 0 && "border-foreground",
          )}
        >
          <span className="inline-flex items-center gap-[var(--esp-2)]">
            <IconeFiltro />
            Filtrar
          </span>
          <span className={ativos > 0 ? "font-semibold" : "font-normal text-muted-foreground"}>
            {descricao ?? "nenhum ativo"}
          </span>
        </button>
      )}

      {folhaAberta && (
        // Fundo escurecido: tocar fora fecha a folha.
        <div ref={fundo} aria-hidden className="fixed inset-0 z-50 bg-foreground/40 md:hidden" onClick={fechar} />
      )}

      <div
        ref={folha}
        id={idFolha}
        role={folhaAberta ? "dialog" : undefined}
        aria-modal={folhaAberta || undefined}
        aria-labelledby={idTitulo}
        data-aberto={folhaAberta || undefined}
        className={sempreVisivel ? undefined : "folha-filtros"}
      >
        <div className={cn("items-center justify-between gap-3 pb-[var(--esp-3)]", folhaAberta ? "flex" : "hidden")}>
          <h2 id={idTitulo} className="text-2xl">
            {titulo}
          </h2>
          <button
            type="button"
            onClick={fechar}
            aria-label="Fechar os filtros"
            className="flex size-11 items-center justify-center rounded-[2px] focus-visible:outline-2 focus-visible:outline-bronze"
          >
            <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        {!folhaAberta && (
          <h2 id={idTitulo} className="sr-only">
            {titulo}
          </h2>
        )}

        <form method="get" action={actionComAncora} onSubmit={aplicar} className="flex flex-col gap-[var(--esp-4)]">
          {Object.entries(ocultos ?? {}).map(([nome, valor]) =>
            valor ? <input key={nome} type="hidden" name={nome} value={valor} /> : null,
          )}
          <div className={cn("grid gap-[var(--esp-4)]", !sempreVisivel && "md:grid-cols-3", sempreVisivel && "sm:grid-cols-2")}>
            {children}
          </div>
          <div
            className={cn(
              "grid grid-cols-2 gap-[var(--esp-3)]",
              folhaAberta && "sticky bottom-0 -mx-4 border-t border-border bg-background px-4 py-[var(--esp-3)]",
              !folhaAberta && "sm:flex sm:items-center",
            )}
          >
            <button type="submit" className="botao order-2 w-full sm:w-auto" disabled={aplicando}>
              {aplicando ? "Aplicando…" : rotuloAplicar}
            </button>
            {ativos > 0 || folhaAberta ? (
              <Link
                href={limparHref}
                scroll={false}
                onClick={() => setAberto(false)}
                className="botao-linha order-1 w-full sm:order-3 sm:w-auto"
              >
                Limpar
              </Link>
            ) : (
              <span aria-hidden className="order-1" />
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

function IconeFiltro() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
      <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="17" r="2" />
    </svg>
  );
}
