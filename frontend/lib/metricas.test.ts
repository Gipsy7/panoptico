import { describe, expect, it } from "vitest";

import {
  caminhoContavel,
  categorizarOrigem,
  deveIgnorar,
  montarBusca,
  montarVisita,
  origemGuardada,
  secaoDoId,
  tipoDeAparelho,
} from "@/lib/metricas";

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
  it("origem e aparelho vão em todo beacon", () => {
    expect(montarVisita("/", true, "direto", "celular")).toEqual({
      caminho: "/",
      nova: true,
      origem: "direto",
      aparelho: "celular",
    });
    expect(montarVisita("/projetos", false, "google", "computador")).toEqual({
      caminho: "/projetos",
      nova: false,
      origem: "google",
      aparelho: "computador",
    });
  });
  it("tipo de aparelho", () => {
    expect(tipoDeAparelho(true)).toBe("celular");
    expect(tipoDeAparelho(false)).toBe("computador");
  });
});

describe("origemGuardada", () => {
  it("só aceita categorias da lista", () => {
    expect(origemGuardada("google")).toBe("google");
    expect(origemGuardada("1")).toBeNull();
    expect(origemGuardada(null)).toBeNull();
    expect(origemGuardada("https://x.com")).toBeNull();
  });
});

describe("secaoDoId", () => {
  it("reconhece o id do título ou a âncora", () => {
    expect(secaoDoId("gastos-titulo")).toBe("gastos");
    expect(secaoDoId("#votos-tema-titulo")).toBe("votos-tema");
    expect(secaoDoId("partido-cotas")).toBeNull();
    expect(secaoDoId(undefined)).toBeNull();
  });
});

describe("montarBusca", () => {
  const dims = { origem: "direto", aparelho: "celular" } as const;
  it("leva UF e cidade só quando houve resultado e no formato certo", () => {
    expect(montarBusca(dims, "cep", true, "SC", "4205407")).toEqual({ ...dims, forma: "cep", resultado: true, uf: "SC", ibge: "4205407" });
    expect(montarBusca(dims, "cep", false, "SC", "4205407")).toEqual({ ...dims, forma: "cep", resultado: false });
    expect(montarBusca(dims, "estado", true, "SC", null)).toEqual({ ...dims, forma: "estado", resultado: true, uf: "SC" });
  });
  it("nunca deixa passar um CEP no lugar da UF ou do IBGE", () => {
    const c = montarBusca(dims, "cep", true, "01310100", "01310100");
    expect(JSON.stringify(c)).not.toContain("01310100");
  });
});
