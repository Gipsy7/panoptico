"use client";

/**
 * Cola entre as funções puras de `avisos.ts` e as APIs do navegador. Só roda no cliente, depois da
 * hidratação (o servidor não tem service worker, Notification nem PushManager).
 */
import {
  type AlvoTipo,
  type MinhasAvisos,
  type PermissaoAviso,
  type RespostaAviso,
  type Suporte,
  chaveVapidParaBytes,
  corpoAlvo,
  corpoInscricao,
  detectarSuporte,
  identidade,
  postarAviso,
} from "@/lib/avisos";
import { API_AVISOS as API, VAPID_PUBLICA } from "@/lib/avisos-config";


const buscar = (url: string, init: RequestInit) => fetch(url, init);
const postar = <T>(caminho: string, corpo: unknown) => postarAviso<T>(buscar, API, caminho, corpo);

export function lerSuporte(): Suporte {
  const instalado =
    (navigator as Navigator & { standalone?: boolean }).standalone === true ||
    window.matchMedia("(display-mode: standalone)").matches;
  return detectarSuporte({
    userAgent: navigator.userAgent,
    plataforma: navigator.platform,
    pontosDeToque: navigator.maxTouchPoints,
    instalado,
    temServiceWorker: "serviceWorker" in navigator,
    temPushManager: "PushManager" in window,
    temNotification: "Notification" in window,
  });
}

export function lerPermissao(): PermissaoAviso {
  return "Notification" in window ? Notification.permission : "indisponivel";
}

/** Inscrição que o navegador já tem para este site (sem pedir nada, sem registrar nada novo). */
export async function inscricaoAtual(): Promise<PushSubscription | null> {
  try {
    const registro = await navigator.serviceWorker.getRegistration("/");
    return (await registro?.pushManager.getSubscription()) ?? null;
  } catch {
    return null;
  }
}

/** O que o servidor sabe deste aparelho. Nulo se a inscrição não existe ou o servidor não confirma. */
export async function consultarMinhas(sub: PushSubscription): Promise<RespostaAviso<MinhasAvisos>> {
  const id = identidade(sub.toJSON() as never);
  if (!id) return { ok: false, status: 0, mensagem: "Inscrição incompleta." };
  return postar<MinhasAvisos>("/avisos/minhas", id);
}

export type ResultadoAtivar = { ok: true } | { ok: false; motivo: "negado" | "erro"; mensagem: string };

/**
 * Ativa os avisos de um alvo. Pede a permissão (precisa vir de um clique), inscreve o aparelho e só
 * então liga o alvo. Se o servidor recusar, desfaz o que criou no navegador: nunca fica "ativo"
 * sem a resposta `ok` do servidor.
 */
export async function ativar(alvoTipo: AlvoTipo, alvoChave: string): Promise<ResultadoAtivar> {
  const permissao = await Notification.requestPermission();
  if (permissao !== "granted") {
    return { ok: false, motivo: permissao === "denied" ? "negado" : "erro", mensagem: "A permissão para avisos não foi dada." };
  }

  let criou = false;
  let sub: PushSubscription | null = null;
  try {
    const registro = await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;
    sub = await registro.pushManager.getSubscription();
    if (!sub) {
      sub = await registro.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: chaveVapidParaBytes(VAPID_PUBLICA),
      });
      criou = true;
    }
  } catch {
    return { ok: false, motivo: "erro", mensagem: "O navegador não conseguiu preparar os avisos neste aparelho." };
  }

  const desfazer = async () => {
    if (criou && sub) await sub.unsubscribe().catch(() => false);
  };

  const json = sub.toJSON() as never;
  const corpo = corpoInscricao(json);
  const id = identidade(json);
  if (!corpo || !id) {
    await desfazer();
    return { ok: false, motivo: "erro", mensagem: "O navegador devolveu uma inscrição incompleta." };
  }

  const inscrita = await postar("/avisos/inscrever", corpo);
  if (!inscrita.ok) {
    await desfazer();
    return { ok: false, motivo: "erro", mensagem: inscrita.mensagem };
  }
  const alvo = await postar("/avisos/alvo", corpoAlvo(id, alvoTipo, alvoChave, "adicionar"));
  if (!alvo.ok) {
    if (criou) {
      await postar("/avisos/cancelar", id);
      await desfazer();
    }
    return { ok: false, motivo: "erro", mensagem: alvo.mensagem };
  }
  return { ok: true };
}

export async function mudarAlvo(sub: PushSubscription, alvoTipo: AlvoTipo, alvoChave: string, acao: "adicionar" | "remover") {
  const id = identidade(sub.toJSON() as never);
  if (!id) return { ok: false as const, status: 0, mensagem: "Inscrição incompleta." };
  return postar<{ ok: boolean; alvos: number }>("/avisos/alvo", corpoAlvo(id, alvoTipo, alvoChave, acao));
}

/** Cancela tudo: o servidor apaga a inscrição e o aparelho desfaz a dele. */
export async function cancelarTodos(sub: PushSubscription): Promise<RespostaAviso<{ ok: boolean }>> {
  const id = identidade(sub.toJSON() as never);
  if (!id) return { ok: false, status: 0, mensagem: "Inscrição incompleta." };
  const r = await postar<{ ok: boolean }>("/avisos/cancelar", id);
  // 404: o servidor já não a tem; o aparelho também deve esquecê-la.
  if (r.ok || r.status === 404) {
    await sub.unsubscribe().catch(() => false);
    return { ok: true, dados: { ok: true } };
  }
  return r;
}
