"use client";

/**
 * "Tudo em detalhe": as seções da página agrupadas em abas, UMA vez no DOM. As mesmas seções
 * viram gaveta (painel que sobe de baixo) quando o endereço é `#ver-<secao>`, que é o link
 * dos <CartaoNumero> do topo.
 *
 * Como funciona:
 * - Toque num cartão: o clique é interceptado, fazemos `history.pushState(#ver-<secao>)` e a
 *   seção ganha a apresentação de gaveta (fixed, fundo esmaecido, botão Fechar com foco).
 *   Fechar (botão, fundo, Esc ou o Voltar do celular) = voltar o histórico, então o Voltar do
 *   celular fecha a gaveta em vez de sair da página. Se a página abriu direto em `#ver-…`
 *   (link compartilhado), fechar só tira o hash (`replaceState`), sem sair do site.
 * - Qualquer outro `#id` que caia numa aba escondida (ex.: `#votos-titulo` da paginação)
 *   ativa essa aba antes de rolar. `#id` de um <details> abre o <details>.
 * - Sem JavaScript, o HTML traz TODOS os painéis visíveis, empilhados (os cartões do topo
 *   continuam apontando para algo visível). Com JavaScript, o script inline do layout marca
 *   `html[data-js]` e uma regra de CSS esconde os painéis `data-ativa="false"` desde o primeiro
 *   paint; depois de montar, o cliente passa a usar `hidden="until-found"` nos inativos, e a
 *   busca do navegador (Ctrl+F) acha o texto e abre a aba.
 * - Seção que não rendeu nada (componente devolveu null) some; aba sem nenhuma seção some.
 *
 * Uso (servidor):
 *   <AbasDetalhe titulo="Tudo em detalhe" abas={[
 *     { id: "dinheiro", rotulo: "Dinheiro", secoes: [
 *       { id: "gastos", titulo: "Gastos do gabinete", conteudo: <GastosSecao … /> },
 *     ] },
 *   ]} />
 */
import { type KeyboardEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";

export type SecaoDetalhe = { id: string; titulo: string; conteudo: ReactNode };
export type AbaDetalhe = { id: string; rotulo: string; secoes: SecaoDetalhe[] };

const PREFIXO = "ver-";

export function AbasDetalhe({ titulo, abas }: { titulo: string; abas: AbaDetalhe[] }) {
  const abaDaSecao = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const a of abas) for (const s of a.secoes) mapa.set(s.id, a.id);
    return mapa;
  }, [abas]);
  const tituloDaSecao = useMemo(
    () => new Map(abas.flatMap((a) => a.secoes.map((s) => [s.id, s.titulo] as const))),
    [abas],
  );

  const [ativa, setAtiva] = useState(abas[0]?.id ?? "");
  const [gaveta, setGaveta] = useState<string | null>(null);
  const [vazias, setVazias] = useState<Set<string>>(new Set());
  const raiz = useRef<HTMLElement>(null);
  const botaoFechar = useRef<HTMLButtonElement>(null);
  const abridor = useRef<HTMLElement | null>(null);

  // Lê o hash atual e põe a página no estado que ele pede.
  const aplicarHash = useCallback(
    (rolar: boolean) => {
      const hash = decodeURIComponent(window.location.hash.slice(1));
      if (hash.startsWith(PREFIXO) && abaDaSecao.has(hash.slice(PREFIXO.length))) {
        const secao = hash.slice(PREFIXO.length);
        setAtiva(abaDaSecao.get(secao)!);
        setGaveta(secao);
        return;
      }
      setGaveta(null);
      if (!hash) return;
      const alvo = document.getElementById(hash);
      const painel = alvo?.closest<HTMLElement>("[data-aba]");
      if (!alvo || !painel || !raiz.current?.contains(painel)) {
        if (alvo instanceof HTMLDetailsElement) alvo.open = true;
        if (alvo && rolar) alvo.scrollIntoView();
        return;
      }
      flushSync(() => setAtiva(painel.dataset.aba!));
      if (alvo instanceof HTMLDetailsElement) alvo.open = true;
      if (rolar) alvo.scrollIntoView();
    },
    [abaDaSecao],
  );

  // Ao montar: descobre seções vazias e aplica o hash de entrada.
  useEffect(() => {
    const el = raiz.current;
    if (!el) return;
    const sem = new Set<string>();
    for (const painel of el.querySelectorAll<HTMLElement>("[data-aba]")) {
      if (!painel.querySelector("[data-secao]:not(:empty)")) sem.add(painel.dataset.aba!);
    }
    const quadro = requestAnimationFrame(() => {
      setVazias(sem);
      setAtiva((atual) => (sem.has(atual) ? (abas.find((a) => !sem.has(a.id))?.id ?? atual) : atual));
      aplicarHash(true);
    });
    return () => cancelAnimationFrame(quadro);
  }, [abas, aplicarHash]);

  // Voltar/avançar do navegador e links comuns com hash.
  useEffect(() => {
    const aoNavegar = () => aplicarHash(true);
    const aoVoltar = () => aplicarHash(false);
    window.addEventListener("hashchange", aoNavegar);
    window.addEventListener("popstate", aoVoltar);
    return () => {
      window.removeEventListener("hashchange", aoNavegar);
      window.removeEventListener("popstate", aoVoltar);
    };
  }, [aplicarHash]);

  // Cliques em links: cartão (#ver-…) abre a gaveta sem rolar a página; link para algo dentro
  // de uma aba escondida ativa a aba antes de o navegador (ou o Next) rolar até lá.
  useEffect(() => {
    const aoClicar = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as Element | null)?.closest?.("a[href*='#']");
      if (!(link instanceof HTMLAnchorElement)) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || url.pathname !== window.location.pathname) return;
      const hash = decodeURIComponent(url.hash.slice(1));
      if (hash.startsWith(PREFIXO) && url.search === window.location.search) {
        const secao = hash.slice(PREFIXO.length);
        if (!abaDaSecao.has(secao)) return;
        e.preventDefault();
        abridor.current = link;
        window.history.pushState({ gaveta: secao }, "", `#${PREFIXO}${secao}`);
        setAtiva(abaDaSecao.get(secao)!);
        setGaveta(secao);
        return;
      }
      const painel = hash ? document.getElementById(hash)?.closest<HTMLElement>("[data-aba]") : null;
      if (painel && raiz.current?.contains(painel) && painel.dataset.aba !== ativa) {
        flushSync(() => setAtiva(painel.dataset.aba!));
      }
    };
    document.addEventListener("click", aoClicar, true);
    return () => document.removeEventListener("click", aoClicar, true);
  }, [abaDaSecao, ativa]);

  const fechar = useCallback(() => {
    if (!gaveta) return;
    const nossa = window.history.state?.gaveta === gaveta && window.location.hash === `#${PREFIXO}${gaveta}`;
    if (nossa) {
      window.history.back();
    } else {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      setGaveta(null);
    }
  }, [gaveta]);

  // Gaveta aberta: trava a rolagem do fundo, foca o Fechar, Esc fecha, Tab fica dentro.
  useEffect(() => {
    if (!gaveta) return;
    const painel = document.getElementById(`${PREFIXO}${gaveta}`);
    const html = document.documentElement;
    const antes = html.style.overflow;
    html.style.overflow = "hidden";
    // O painel da aba pode ainda estar com hidden="until-found" (o efeito das abas roda depois
    // deste): escondido, o botão não recebe foco e ele ficava no link de fora da gaveta.
    painel?.closest<HTMLElement>("[data-aba]")?.removeAttribute("hidden");
    const focarFechar = () => botaoFechar.current?.focus({ preventScroll: true });
    focarFechar();
    const quadroFoco = requestAnimationFrame(() => {
      if (!painel?.contains(document.activeElement)) focarFechar();
    });
    painel?.scrollTo({ top: 0 });
    const aoTeclar = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        fechar();
        return;
      }
      if (e.key !== "Tab" || !painel) return;
      const focaveis = [
        ...painel.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), select, input, textarea, summary, [tabindex]:not([tabindex='-1'])",
        ),
      ].filter((el) => el.offsetParent !== null);
      if (focaveis.length === 0) return;
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (e.shiftKey && document.activeElement === primeiro) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primeiro.focus();
      }
    };
    document.addEventListener("keydown", aoTeclar);
    return () => {
      cancelAnimationFrame(quadroFoco);
      document.removeEventListener("keydown", aoTeclar);
      html.style.overflow = antes;
      const volta =
        abridor.current ?? document.querySelector<HTMLElement>(`a[href="#${PREFIXO}${gaveta}"]`);
      volta?.focus({ preventScroll: true });
      abridor.current = null;
    };
  }, [gaveta, fechar]);

  // Abas inativas: "until-found" deixa a busca do navegador achar o texto e abrir a aba.
  useEffect(() => {
    const el = raiz.current;
    if (!el) return;
    const paineis = [...el.querySelectorAll<HTMLElement>("[data-aba]")];
    for (const p of paineis) {
      if (p.dataset.aba !== ativa) p.setAttribute("hidden", "until-found");
      else p.removeAttribute("hidden");
    }
    const aoAchar = (e: Event) => setAtiva((e.currentTarget as HTMLElement).dataset.aba!);
    for (const p of paineis) p.addEventListener("beforematch", aoAchar);
    return () => {
      for (const p of paineis) p.removeEventListener("beforematch", aoAchar);
    };
  }, [ativa, vazias]);

  const visiveis = abas.filter((a) => !vazias.has(a.id));

  const aoTeclarAba = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = visiveis.findIndex((a) => a.id === ativa);
    let j = -1;
    if (e.key === "ArrowRight") j = (i + 1) % visiveis.length;
    else if (e.key === "ArrowLeft") j = (i - 1 + visiveis.length) % visiveis.length;
    else if (e.key === "Home") j = 0;
    else if (e.key === "End") j = visiveis.length - 1;
    if (j < 0) return;
    e.preventDefault();
    setAtiva(visiveis[j].id);
    document.getElementById(`aba-${visiveis[j].id}-botao`)?.focus();
  };

  return (
    <section ref={raiz} aria-labelledby="detalhe-titulo" className="flex min-w-0 flex-col">
      <h2 id="detalhe-titulo" className="mb-2 text-2xl">
        {titulo}
      </h2>
      <div
        role="tablist"
        aria-label={titulo}
        className="sticky top-14 z-30 -mx-4 flex snap-x snap-proximity gap-1 overflow-x-auto border-b border-border bg-background px-4 [scrollbar-width:none] lg:mx-0 lg:px-0"
      >
        {visiveis.map((a) => {
          const eAtiva = a.id === ativa;
          return (
            <button
              key={a.id}
              type="button"
              role="tab"
              id={`aba-${a.id}-botao`}
              aria-selected={eAtiva}
              aria-controls={`aba-${a.id}`}
              tabIndex={eAtiva ? 0 : -1}
              onClick={() => setAtiva(a.id)}
              onKeyDown={aoTeclarAba}
              className={`flex min-h-11 shrink-0 snap-start items-center border-b-2 px-3 text-sm whitespace-nowrap focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-bronze ${
                eAtiva
                  ? "border-bronze font-semibold text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {a.rotulo}
            </button>
          );
        })}
      </div>

      {abas.map((a) => (
        <div
          key={a.id}
          role="tabpanel"
          id={`aba-${a.id}`}
          data-aba={a.id}
          aria-labelledby={`aba-${a.id}-botao`}
          data-ativa={a.id === ativa}
          className="pagina-secoes min-w-0 pt-6"
        >
          {a.secoes.map((s) => {
            const aberta = gaveta === s.id;
            return (
              <div
                key={s.id}
                id={`${PREFIXO}${s.id}`}
                data-secao={s.id}
                role={aberta ? "dialog" : undefined}
                aria-modal={aberta ? true : undefined}
                aria-label={aberta ? tituloDaSecao.get(s.id) : undefined}
                className={
                  aberta
                    ? "fixed inset-x-0 bottom-0 z-[60] mx-auto flex max-h-[88dvh] w-full max-w-3xl flex-col gap-4 overflow-y-auto overscroll-contain rounded-t-xl border-t border-border bg-background px-4 pb-8 shadow-[var(--sombra-menu)] motion-safe:animate-in motion-safe:slide-in-from-bottom-8 motion-safe:fade-in motion-safe:duration-200"
                    : "min-w-0 scroll-mt-28 empty:hidden"
                }
              >
                {aberta && (
                  <div className="sticky top-0 z-10 -mx-4 flex flex-col items-center gap-1 border-b border-border bg-background px-4 pt-2 pb-2">
                    <span aria-hidden className="h-1 w-10 rounded-full bg-border" />
                    <div className="flex w-full items-center justify-between gap-3">
                      <p className="min-w-0 truncate text-sm text-muted-foreground">{a.rotulo}</p>
                      <button ref={botaoFechar} type="button" onClick={fechar} className="botao-linha shrink-0">
                        Fechar
                      </button>
                    </div>
                  </div>
                )}
                {s.conteudo}
              </div>
            );
          })}
        </div>
      ))}

      {gaveta && (
        <div
          aria-hidden
          onClick={fechar}
          className="fixed inset-0 z-[55] bg-background/80 backdrop-blur-sm motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
        />
      )}
    </section>
  );
}
