import { describe, expect, it } from "vitest";

import {
  CHAVE_LEITURA_FACIL,
  ESCONDIDO_NA_LEITURA_FACIL,
  gravarPreferencia,
  juntar,
  lerPreferencia,
  textoEscondido,
} from "./leitura-facil";

describe("leitura fácil", () => {
  it("usa uma chave própria do Panóptico", () => {
    expect(CHAVE_LEITURA_FACIL).toBe("panoptico:leitura-facil");
  });

  it("lê a preferência: só '1' liga", () => {
    expect(lerPreferencia("1")).toBe(true);
    expect(lerPreferencia("0")).toBe(false);
    expect(lerPreferencia(null)).toBe(false);
    expect(lerPreferencia(undefined)).toBe(false);
  });

  it("grava '1' ao ligar e apaga ao desligar", () => {
    expect(gravarPreferencia(true)).toBe("1");
    expect(gravarPreferencia(false)).toBeNull();
  });

  it("junta itens com vírgula e 'e'", () => {
    expect(juntar([])).toBe("");
    expect(juntar(["a"])).toBe("a");
    expect(juntar(["a", "b"])).toBe("a e b");
    expect(juntar(["a", "b", "c"])).toBe("a, b e c");
  });

  it("o quadro lista tudo o que é escondido e diz como ver de novo", () => {
    const t = textoEscondido();
    for (const item of ESCONDIDO_NA_LEITURA_FACIL) expect(t).toContain(item);
    expect(t).toMatch(/^Escondemos /);
    expect(t).toContain("Desligue a chave para ver tudo.");
  });
});
