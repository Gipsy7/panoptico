import { describe, expect, it } from "vitest";

import { moverOpcao, textoResultados } from "./opcao-ativa";

describe("moverOpcao", () => {
  it("desce, sobe e dá a volta", () => {
    expect(moverOpcao(-1, 3, "ArrowDown")).toBe(0);
    expect(moverOpcao(0, 3, "ArrowDown")).toBe(1);
    expect(moverOpcao(2, 3, "ArrowDown")).toBe(0);
    expect(moverOpcao(-1, 3, "ArrowUp")).toBe(2);
    expect(moverOpcao(0, 3, "ArrowUp")).toBe(2);
    expect(moverOpcao(2, 3, "ArrowUp")).toBe(1);
  });
  it("Home e End", () => {
    expect(moverOpcao(1, 5, "Home")).toBe(0);
    expect(moverOpcao(1, 5, "End")).toBe(4);
  });
  it("lista vazia", () => {
    expect(moverOpcao(0, 0, "ArrowDown")).toBe(-1);
  });
});

describe("textoResultados", () => {
  it("singular, plural e nenhum", () => {
    expect(textoResultados(0, "Nada")).toBe("Nada");
    expect(textoResultados(1, "Nada")).toBe("1 resultado");
    expect(textoResultados(8, "Nada")).toBe("8 resultados");
  });
});
