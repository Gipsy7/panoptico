import { describe, expect, it } from "vitest";

import { caminhoContavel, categorizarOrigem, deveIgnorar, montarVisita, tipoDeAparelho } from "@/lib/metricas";

const SITE = "panoptico.social.br";

describe("categorizarOrigem", () => {
  it.each([
    ["", "direto"],
    ["lixo", "direto"],
    ["https://panoptico.social.br/representantes?cep=01310100", "direto"],
    ["https://api.whatsapp.com/send?text=x", "whatsapp"],
    ["https://wa.me/", "whatsapp"],
    ["https://www.google.com/", "google"],
    ["https://www.google.com.br/search?q=a", "google"],
    ["https://notgoogle.com/", "outro_site"],
    ["https://www.bing.com/", "buscadores"],
    ["https://duckduckgo.com/", "buscadores"],
    ["https://l.facebook.com/l.php", "redes"],
    ["https://t.co/abc", "redes"],
    ["https://www.instagram.com/", "redes"],
    ["https://noticias.exemplo.com.br/materia", "outro_site"],
    ["https://evilfacebook.com/", "outro_site"],
  ])("%s -> %s", (referrer, esperado) => {
    expect(categorizarOrigem(referrer, SITE)).toBe(esperado);
  });
});

describe("caminhoContavel", () => {
  it("não conta o painel", () => {
    expect(caminhoContavel("/painel")).toBe(false);
    expect(caminhoContavel("/painel/x")).toBe(false);
    expect(caminhoContavel("/")).toBe(true);
    expect(caminhoContavel("/parlamentar/123")).toBe(true);
  });
});

describe("deveIgnorar", () => {
  it("ignora automação, pedido de não rastrear e aparelho do dono", () => {
    expect(deveIgnorar({ webdriver: true })).toBe(true);
    expect(deveIgnorar({ naoRastrear: true })).toBe(true);
    expect(deveIgnorar({ aparelhoDoDono: "1" })).toBe(true);
    expect(deveIgnorar({ aparelhoDoDono: null })).toBe(false);
    expect(deveIgnorar({})).toBe(false);
  });
});

describe("montarVisita", () => {
  it("origem e aparelho só na primeira página da visita", () => {
    expect(montarVisita("/", true, "direto", "celular")).toEqual({
      caminho: "/",
      nova: true,
      origem: "direto",
      dispositivo: "celular",
    });
    expect(montarVisita("/projetos", false, "google", "computador")).toEqual({ caminho: "/projetos", nova: false });
  });
  it("tipo de aparelho", () => {
    expect(tipoDeAparelho(true)).toBe("celular");
    expect(tipoDeAparelho(false)).toBe("computador");
  });
});
