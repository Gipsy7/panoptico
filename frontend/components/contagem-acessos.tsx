"use client";

/**
 * Contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). As páginas ficam em cache na borda,
 * então a contagem só pode vir do navegador. Cada beacon leva só o caminho da página (sem query
 * nem fragmento, que podem ter CEP), a categoria da origem, o tipo de aparelho e, em ações, o nome
 * do recurso ou da seção. Sem cookie, sem identificador: o início da visita é só a categoria da
 * origem guardada no sessionStorage da aba. Falha em silêncio.
 */
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import {
  CHAVE_SEM_CONTAGEM,
  CHAVE_VISITA,
  type Dims,
  type FormaDeBusca,
  type Recurso,
  caminhoContavel,
  categorizarOrigem,
  deveIgnorar,
  montarBusca,
  montarVisita,
  origemGuardada,
  secaoDoId,
  tipoDeAparelho,
} from "@/lib/metricas";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function ignorar(): boolean {
  try {
    const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
    return deveIgnorar({
      webdriver: nav.webdriver,
      naoRastrear: nav.doNotTrack === "1" || nav.globalPrivacyControl === true,
      aparelhoDoDono: localStorage.getItem(CHAVE_SEM_CONTAGEM),
    });
  } catch {
    return true; // sem acesso ao armazenamento: na dúvida, não conta
  }
}

function enviar(rota: string, corpo: unknown): void {
  try {
    // text/plain é uma requisição "simples": o navegador não faz preflight de CORS.
    navigator.sendBeacon(`${API}/metricas/${rota}`, new Blob([JSON.stringify(corpo)], { type: "text/plain" }));
  } catch {
    // A contagem nunca pode atrapalhar a página.
  }
}

function aparelho() {
  return tipoDeAparelho(window.matchMedia("(pointer: coarse)").matches);
}

/** Origem da visita em curso (guardada ao entrar); sem visita ainda, a do referrer. */
function dimensoes(): Dims {
  let origem = null;
  try {
    origem = origemGuardada(sessionStorage.getItem(CHAVE_VISITA));
  } catch {}
  return {
    origem: origem ?? categorizarOrigem(document.referrer, window.location.hostname),
    aparelho: aparelho(),
  };
}

/** Conta o uso de um recurso (só o nome; nunca o valor digitado). */
export function registrarRecurso(recurso: Recurso): void {
  if (ignorar() || !caminhoContavel(window.location.pathname)) return;
  enviar("recurso", { recurso, ...dimensoes() });
}

/** Conta uma busca de representantes: o resultado e, se houve, a UF e a cidade. Nunca o CEP. */
export function registrarBusca(forma: FormaDeBusca, resultado: boolean, uf?: string | null, ibge?: string | null): void {
  if (ignorar()) return;
  enviar("busca", montarBusca(dimensoes(), forma, resultado, uf, ibge));
}

let ultimoCaminho: string | null = null;

function contarPagina(pathname: string): void {
  if (!caminhoContavel(pathname) || ignorar()) return;
  let origem = null;
  try {
    origem = origemGuardada(sessionStorage.getItem(CHAVE_VISITA));
  } catch {
    return;
  }
  const nova = origem === null;
  if (nova) {
    origem = categorizarOrigem(document.referrer, window.location.hostname);
    try {
      sessionStorage.setItem(CHAVE_VISITA, origem);
    } catch {
      return;
    }
  }
  ultimoCaminho = pathname;
  enviar("visita", montarVisita(pathname, nova, origem ?? "direto", aparelho()));
}

export function ContagemAcessos() {
  const pathname = usePathname();
  const ultimo = useRef<string | null>(null);
  const secoesVistas = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (ultimo.current === pathname) return; // modo estrito do React roda o efeito duas vezes
    ultimo.current = pathname;
    secoesVistas.current = new Set();
    contarPagina(pathname);
  }, [pathname]);

  useEffect(() => {
    const contarSecao = (id: string | null | undefined) => {
      const secao = secaoDoId(id);
      if (!secao || secoesVistas.current.has(secao) || ignorar()) return;
      if (!caminhoContavel(window.location.pathname)) return;
      secoesVistas.current.add(secao);
      enviar("secao", { secao, ...dimensoes() });
    };
    const aoClicar = (e: MouseEvent) => {
      const alvo = e.target as Element | null;
      // Links marcados com data-metrica (ex.: compartilhar no WhatsApp) contam um recurso ao clique.
      if (alvo?.closest?.("[data-metrica]")?.getAttribute("data-metrica") === "compartilhar") {
        registrarRecurso("compartilhar");
      }
      // Atalho do resumo do perfil para uma seção (href="#gastos-titulo").
      const ancora = alvo?.closest?.("a[href^='#']");
      if (ancora) contarSecao(ancora.getAttribute("href"));
    };
    // "toggle" não sobe na árvore: a captura pega o <details> aberto dentro de uma seção do perfil.
    const aoAbrir = (e: Event) => {
      const d = e.target;
      if (!(d instanceof HTMLDetailsElement) || !d.open) return;
      contarSecao(d.closest("section[aria-labelledby]")?.getAttribute("aria-labelledby"));
    };
    // Última página da visita: só o caminho, ao sair da aba ou do site.
    const aoSair = () => {
      if (!ultimoCaminho || ignorar()) return;
      enviar("saida", { caminho: ultimoCaminho, ...dimensoes() });
    };
    document.addEventListener("click", aoClicar);
    document.addEventListener("toggle", aoAbrir, true);
    window.addEventListener("pagehide", aoSair);
    return () => {
      document.removeEventListener("click", aoClicar);
      document.removeEventListener("toggle", aoAbrir, true);
      window.removeEventListener("pagehide", aoSair);
    };
  }, []);

  return null;
}
