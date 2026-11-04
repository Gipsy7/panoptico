import { describe, expect, it } from "vitest";

import {
  contagens,
  dataMaisRecente,
  escolherMosaico,
  formatoDe,
  listaDeFontes,
  textoFora,
  type PessoaMosaico,
} from "./cartao-cidade";

const base = {
  presidente: 1,
  governador: 1,
  prefeito: 1,
  nSenadores: 3,
  nFederais: 16,
  nEstaduais: 40,
  nVereadores: 15,
};

describe("contagens", () => {
  it("soma todos os cargos (Blumenau: 77)", () => {
    const c = contagens(base);
    expect(c.total).toBe(77);
    expect(c.itens.map((i) => i.rotulo)).toEqual([
      "1 presidente",
      "3 senadores",
      "16 deputados federais",
      "1 governador",
      "40 deputados estaduais",
      "1 prefeito",
      "15 vereadores",
    ]);
    expect(c.fora).toEqual([]);
  });

  it("omite o que não tem dado e não conta no total", () => {
    const c = contagens({ ...base, nVereadores: null, prefeito: null });
    expect(c.total).toBe(61);
    expect(c.fora).toEqual(["prefeito", "vereadores"]);
    expect(textoFora(c.fora)).toBe("Dado não publicado: prefeito e vereadores.");
  });

  it("Distrito Federal não tem prefeito nem vereadores", () => {
    const c = contagens({ ...base, distrito: true, nEstaduais: 24 });
    expect(c.total).toBe(1 + 3 + 16 + 1 + 24);
    expect(c.itens.some((i) => i.rotulo.includes("distritais"))).toBe(true);
    expect(c.fora).toEqual([]);
  });
});

describe("escolherMosaico", () => {
  const p = (esfera: PessoaMosaico["esfera"], i: number, foto: boolean): PessoaMosaico => ({
    chave: `${esfera}${i}`,
    esfera,
    foto: foto ? `f${esfera}${i}` : null,
  });
  const todos = [
    p("presidente", 0, true),
    p("governador", 0, false),
    p("prefeito", 0, true),
    ...[0, 1, 2].map((i) => p("senado", i, true)),
    ...Array.from({ length: 16 }, (_, i) => p("federal", i, i % 2 === 0)),
  ];

  it("prioriza quem tem foto e mantém a ordem fixa de cargo", () => {
    const m = escolherMosaico(todos, 6, "4202404");
    expect(m).toHaveLength(6);
    expect(m.every((x) => x.foto)).toBe(true);
    expect(m.map((x) => x.esfera)).toEqual(["presidente", "prefeito", "senado", "senado", "senado", "federal"]);
  });

  it("é estável para a mesma cidade", () => {
    const a = escolherMosaico(todos, 9, "1").map((x) => x.chave);
    expect(escolherMosaico(todos, 9, "1").map((x) => x.chave)).toEqual(a);
  });

  it("corta em linhas inteiras de 3", () => {
    const poucos = [
      p("presidente", 0, false),
      p("senado", 0, true),
      p("senado", 1, true),
      p("senado", 2, true),
      p("senado", 3, true),
    ];
    expect(escolherMosaico(poucos, 6, "x")).toHaveLength(3);
    expect(escolherMosaico([p("senado", 0, true)], 6, "x")).toHaveLength(0);
  });
});

describe("apoio", () => {
  it("formato padrão é feed", () => {
    expect(formatoDe(undefined)).toBe("feed");
    expect(formatoDe("stories")).toBe("stories");
    expect(formatoDe("outro")).toBe("feed");
  });
  it("lista de fontes e data", () => {
    expect(listaDeFontes(["Câmara", "Senado", "TSE", "TSE"])).toBe("Câmara, Senado e TSE");
    expect(dataMaisRecente(["2026-10-01", null, "2026-11-02T10:00:00Z"])).toBe("2026-11-02T10:00:00Z");
  });
});
