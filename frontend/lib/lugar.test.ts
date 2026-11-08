import { describe, expect, it } from "vitest";
import { gravarLugar, hrefDoMenu, lerLugar } from "./lugar";

describe("lugar", () => {
  it("lê e grava", () => {
    const l = { ibge: "4202404", nome: "Blumenau", uf: "SC" };
    expect(lerLugar(gravarLugar(l))).toEqual(l);
  });
  it("ignora valor inválido", () => {
    expect(lerLugar(null)).toBeNull();
    expect(lerLugar("{")).toBeNull();
    expect(lerLugar(JSON.stringify({ ibge: "42", nome: "X", uf: "SC" }))).toBeNull();
  });
  it("destinos do menu", () => {
    const l = { ibge: "4202404", nome: "Blumenau", uf: "SC" };
    expect(hrefDoMenu("Seu lugar", l)).toBe("/cidade/4202404");
    expect(hrefDoMenu("Representantes", l)).toBe("/representantes?municipio=4202404");
    expect(hrefDoMenu("Seu lugar", null)).toBe("/#cep");
  });
});
