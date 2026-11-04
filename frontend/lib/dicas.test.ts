import { describe, expect, it } from "vitest";

import { chaveArmazenamentoDica, DICAS, dicaJaVista, textoDaDica } from "./dicas";

describe("dicas", () => {
  it("uma linha curta por página", () => {
    for (const texto of Object.values(DICAS)) {
      expect(texto.length).toBeLessThanOrEqual(90);
      expect(texto).not.toContain("\n");
    }
  });
  it("busca por chave, sem herdar do protótipo", () => {
    expect(textoDaDica("cidade")).toBe(DICAS.cidade);
    expect(textoDaDica("toString")).toBeNull();
    expect(textoDaDica("nada")).toBeNull();
  });
  it("chave de armazenamento própria", () => {
    expect(chaveArmazenamentoDica("projetos")).toBe("panoptico.dica.projetos");
    expect(dicaJaVista("1")).toBe(true);
    expect(dicaJaVista(undefined)).toBe(false);
  });
});
