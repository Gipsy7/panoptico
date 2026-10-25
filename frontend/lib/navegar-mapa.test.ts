import { describe, expect, it } from "vitest";

import { buscarNoMapa, moverNoMapa, normalizar, ordenarPorNome } from "./navegar-mapa";

describe("ordenarPorNome", () => {
  it("ordena como em português, ignorando acento e caixa, sem mudar a lista original", () => {
    const itens = [
      { id: "SP", nome: "São Paulo" },
      { id: "AM", nome: "Amazonas" },
      { id: "AP", nome: "Amapá" },
      { id: "SC", nome: "Santa Catarina" },
      { id: "AC", nome: "Acre" },
    ];
    expect(ordenarPorNome(itens).map((i) => i.id)).toEqual(["AC", "AP", "AM", "SC", "SP"]);
    expect(itens[0].id).toBe("SP");
  });
  it("nomes iguais desempatam pelo id (ordem estável)", () => {
    const itens = [
      { id: "2", nome: "Bom Jesus" },
      { id: "1", nome: "Bom Jesus" },
    ];
    expect(ordenarPorNome(itens).map((i) => i.id)).toEqual(["1", "2"]);
  });
});

describe("moverNoMapa", () => {
  it("setas andam um e param nas pontas", () => {
    expect(moverNoMapa(0, 3, "ArrowRight")).toBe(1);
    expect(moverNoMapa(1, 3, "ArrowDown")).toBe(2);
    expect(moverNoMapa(2, 3, "ArrowDown")).toBe(2);
    expect(moverNoMapa(2, 3, "ArrowLeft")).toBe(1);
    expect(moverNoMapa(0, 3, "ArrowUp")).toBe(0);
  });
  it("Home e End", () => {
    expect(moverNoMapa(1, 5, "Home")).toBe(0);
    expect(moverNoMapa(1, 5, "End")).toBe(4);
  });
  it("sem item atual começa do primeiro; lista vazia dá -1", () => {
    expect(moverNoMapa(-1, 3, "ArrowDown")).toBe(0);
    expect(moverNoMapa(-1, 3, "ArrowUp")).toBe(0);
    expect(moverNoMapa(0, 0, "ArrowDown")).toBe(-1);
  });
});

describe("buscarNoMapa", () => {
  const nomes = ["Acre", "Alagoas", "Amapá", "Santa Catarina", "São Paulo", "Sergipe"];
  it("uma letra vai ao próximo nome com ela e dá a volta", () => {
    expect(buscarNoMapa(nomes, 0, "s")).toBe(3);
    expect(buscarNoMapa(nomes, 3, "s")).toBe(4);
    expect(buscarNoMapa(nomes, 5, "s")).toBe(3);
    expect(buscarNoMapa(nomes, 5, "a")).toBe(0);
  });
  it("várias letras procuram a partir do atual, sem acento", () => {
    expect(buscarNoMapa(nomes, 3, "sa")).toBe(3);
    expect(buscarNoMapa(nomes, 3, "sao")).toBe(4);
    expect(buscarNoMapa(nomes, 0, "AMA")).toBe(2);
  });
  it("letra repetida percorre os nomes com aquela letra", () => {
    expect(buscarNoMapa(nomes, 3, "ss")).toBe(4);
  });
  it("sem combinação, -1; sem item atual, começa do primeiro", () => {
    expect(buscarNoMapa(nomes, 0, "z")).toBe(-1);
    expect(buscarNoMapa(nomes, -1, "a")).toBe(0);
    expect(buscarNoMapa([], 0, "a")).toBe(-1);
  });
  it("normalizar tira acento e caixa", () => {
    expect(normalizar("São PAULO")).toBe("sao paulo");
  });
});
