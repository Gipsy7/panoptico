import { describe, expect, it, vi } from "vitest";

import {
  acompanhaAlvo,
  caminhoSeguro,
  chaveAlvo,
  chaveVapidParaBytes,
  corpoAlvo,
  corpoInscricao,
  detectarSuporte,
  estadoInicial,
  identidade,
  postarAviso,
} from "./avisos";

const COMPLETO = { temServiceWorker: true, temPushManager: true, temNotification: true, instalado: false };
const NADA = { temServiceWorker: false, temPushManager: false, temNotification: false, instalado: false };
const UA_ANDROID = "Mozilla/5.0 (Linux; Android 14) Chrome/130 Mobile Safari/537.36";
const UA_IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1";

describe("detectarSuporte", () => {
  it("aceita quem tem service worker, push e notificação", () => {
    expect(detectarSuporte({ ...COMPLETO, userAgent: UA_ANDROID })).toBe("suportado");
  });
  it("iPhone sem instalar pede para adicionar à tela inicial", () => {
    expect(detectarSuporte({ ...NADA, temServiceWorker: true, userAgent: UA_IPHONE })).toBe("ios-instalar");
  });
  it("iPad que se apresenta como Mac também", () => {
    expect(detectarSuporte({ ...NADA, userAgent: "Mozilla/5.0 (Macintosh)", plataforma: "MacIntel", pontosDeToque: 5 })).toBe("ios-instalar");
  });
  it("iPhone instalado, com tudo, é suportado", () => {
    expect(detectarSuporte({ ...COMPLETO, instalado: true, userAgent: UA_IPHONE })).toBe("suportado");
  });
  it("navegador interno do WhatsApp sem suporte tem instrução própria", () => {
    expect(detectarSuporte({ ...NADA, userAgent: `${UA_ANDROID} WhatsApp/2.24` })).toBe("app-interno");
  });
  it("computador antigo sem suporte", () => {
    expect(detectarSuporte({ ...NADA, userAgent: "Mozilla/5.0 (Windows NT 10.0)" })).toBe("sem-suporte");
  });
});

describe("estadoInicial", () => {
  it("sem suporte ou sem API de notificação", () => {
    expect(estadoInicial("ios-instalar", "default", false)).toBe("sem-suporte");
    expect(estadoInicial("suportado", "indisponivel", false)).toBe("sem-suporte");
  });
  it("permissão negada", () => {
    expect(estadoInicial("suportado", "denied", false)).toBe("negado");
  });
  it("ativo só com permissão e o servidor confirmando o alvo", () => {
    expect(estadoInicial("suportado", "granted", true)).toBe("ativo");
    expect(estadoInicial("suportado", "granted", false)).toBe("pronto");
    expect(estadoInicial("suportado", "default", true)).toBe("pronto");
  });
});

describe("chaves e caminhos", () => {
  it("monta a chave do alvo", () => {
    expect(chaveAlvo("camara", "204554")).toBe("camara:204554");
    expect(chaveAlvo("senado", 5012)).toBe("senado:5012");
    expect(chaveAlvo("camara", null)).toBeNull();
    expect(chaveAlvo(undefined, "1")).toBeNull();
    expect(chaveAlvo("camara", " ")).toBeNull();
  });
  it("só aceita caminho do próprio site", () => {
    expect(caminhoSeguro("/parlamentar/10")).toBe("/parlamentar/10");
    expect(caminhoSeguro("//outro.example/x")).toBeNull();
    expect(caminhoSeguro("https://outro.example")).toBeNull();
    expect(caminhoSeguro("/\\outro.example")).toBeNull();
    expect(caminhoSeguro(undefined)).toBeNull();
  });
  it("converte a chave VAPID em bytes", () => {
    // "AQID" = [1, 2, 3]; "-_8" = bytes 0xfb 0xff (alfabeto da URL, sem preenchimento)
    expect(Array.from(chaveVapidParaBytes("AQID"))).toEqual([1, 2, 3]);
    expect(Array.from(chaveVapidParaBytes("-_8"))).toEqual([0xfb, 0xff]);
  });
});

describe("corpos de pedido", () => {
  const sub = { endpoint: "https://push.example/abc", keys: { p256dh: "P", auth: "A" } };
  it("inscrição e identidade", () => {
    expect(corpoInscricao(sub)).toEqual({ endpoint: sub.endpoint, p256dh: "P", auth: "A" });
    expect(identidade(sub)).toEqual({ endpoint: sub.endpoint, auth: "A" });
  });
  it("inscrição incompleta vira nulo", () => {
    expect(corpoInscricao({ endpoint: "x", keys: { auth: "A" } })).toBeNull();
    expect(identidade({ endpoint: "", keys: { auth: "A" } })).toBeNull();
  });
  it("corpo do alvo", () => {
    expect(corpoAlvo({ endpoint: "e", auth: "a" }, "parlamentar", "camara:1", "adicionar")).toEqual({
      endpoint: "e",
      auth: "a",
      alvo_tipo: "parlamentar",
      alvo_chave: "camara:1",
      acao: "adicionar",
    });
  });
});

describe("postarAviso", () => {
  const resposta = (status: number, corpo: unknown) => new Response(JSON.stringify(corpo), { status });
  it("devolve os dados quando o servidor responde ok", async () => {
    const buscar = vi.fn(async () => resposta(200, { ok: true }));
    const r = await postarAviso<{ ok: boolean }>(buscar, "https://api.example", "/avisos/inscrever", { a: 1 });
    expect(r).toEqual({ ok: true, dados: { ok: true } });
    expect(buscar).toHaveBeenCalledWith("https://api.example/avisos/inscrever", expect.objectContaining({ method: "POST" }));
  });
  it("não dá por feito o que o servidor recusou", async () => {
    const r = await postarAviso(vi.fn(async () => resposta(503, {})), "", "/x", {});
    expect(r).toMatchObject({ ok: false, status: 503 });
    const limite = await postarAviso(vi.fn(async () => resposta(429, {})), "", "/x", {});
    expect(limite).toMatchObject({ ok: false, status: 429 });
  });
  it("falha de rede vira erro, não exceção", async () => {
    const r = await postarAviso(vi.fn(async () => Promise.reject(new TypeError("rede"))), "", "/x", {});
    expect(r).toMatchObject({ ok: false, status: 0 });
  });
  it("corpo que não é JSON vira erro", async () => {
    const r = await postarAviso(vi.fn(async () => new Response("não é json", { status: 200 })), "", "/x", {});
    expect(r.ok).toBe(false);
  });
});

describe("acompanhaAlvo", () => {
  const minhas = {
    alvos: [{ alvo_tipo: "parlamentar" as const, alvo_chave: "camara:1", nome: "Fulano", caminho: "/parlamentar/1" }],
    novidades: [],
  };
  it("confere tipo e chave", () => {
    expect(acompanhaAlvo(minhas, "parlamentar", "camara:1")).toBe(true);
    expect(acompanhaAlvo(minhas, "projeto", "camara:1")).toBe(false);
    expect(acompanhaAlvo(minhas, "parlamentar", "camara:2")).toBe(false);
  });
});
