"use client";

/**
 * Contagem anônima de acessos (docs/DECISOES.md, 2026-10-31). As páginas ficam em cache na borda,
 * então a contagem só pode vir do navegador. Manda um beacon com o caminho (sem query nem
 * fragmento, que podem ter CEP), a categoria da origem e o tipo de aparelho. Sem cookie, sem
 * identificador: o início da visita é só um "1" no sessionStorage da aba. Falha em silêncio.
 */
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import {
  CHAVE_SEM_CONTAGEM,
  CHAVE_VISITA,
  type Recurso,
  caminhoContavel,
  categorizarOrigem,
  deveIgnorar,
  montarVisita,
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

/** Conta o uso de um recurso (só o nome; nunca o valor digitado). */
export function registrarRecurso(recurso: Recurso): void {
  if (ignorar() || !caminhoContavel(window.location.pathname)) return;
  enviar("recurso", { recurso });
}

function contarPagina(pathname: string): void {
  if (!caminhoContavel(pathname) || ignorar()) return;
  let nova = false;
  try {
    nova = sessionStorage.getItem(CHAVE_VISITA) !== "1";
    if (nova) sessionStorage.setItem(CHAVE_VISITA, "1");
  } catch {
    return;
  }
  const origem = categorizarOrigem(document.referrer, window.location.hostname);
  const aparelho = tipoDeAparelho(window.matchMedia("(pointer: coarse)").matches);
  enviar("visita", montarVisita(pathname, nova, origem, aparelho));
}

export function ContagemAcessos() {
  const pathname = usePathname();
  const ultimo = useRef<string | null>(null);

  useEffect(() => {
    if (ultimo.current === pathname) return; // modo estrito do React roda o efeito duas vezes
    ultimo.current = pathname;
    contarPagina(pathname);
  }, [pathname]);

  // Links marcados com data-metrica (ex.: compartilhar no WhatsApp) contam um recurso ao clique.
  useEffect(() => {
    const aoClicar = (e: MouseEvent) => {
      const alvo = (e.target as Element | null)?.closest?.("[data-metrica]");
      const nome = alvo?.getAttribute("data-metrica");
      if (nome === "compartilhar") registrarRecurso(nome);
    };
    document.addEventListener("click", aoClicar);
    return () => document.removeEventListener("click", aoClicar);
  }, []);

  return null;
}
