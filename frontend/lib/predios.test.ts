import { describe, expect, it } from "vitest";

import { contagem, faixaEstado, larguraFaixa, medidasDoDesenho, predioInicial, roteiroDaMao } from "@/lib/predios";

describe("desenho dos prédios", () => {
  it("monta a faixa do estado com a capital", () => {
    expect(faixaEstado("SC", "Santa Catarina")).toBe("SANTA CATARINA · FLORIANÓPOLIS");
  });
  it("sem capital conhecida, usa só o estado", () => {
    expect(faixaEstado("XX", "Outro Lugar")).toBe("OUTRO LUGAR");
  });
  it("mantém a faixa dentro do desenho de 360", () => {
    expect(larguraFaixa(faixaEstado("MS", "Mato Grosso do Sul"))).toBeLessThanOrEqual(340);
  });
  it("conta no singular e no plural", () => {
    expect(contagem(1, "senador", "senadores")).toBe("1 senador");
    expect(contagem(3, "senador", "senadores")).toBe("3 senadores");
  });
  it("o roteiro da mão pula prédios que não existem", () => {
    expect(roteiroDaMao(["planalto", "senado", "camara", "governo"])).toEqual(["senado", "planalto", "governo", "camara"]);
  });
  it("o desenho sem cidade é mais curto", () => {
    expect(medidasDoDesenho(false).altura).toBeLessThan(medidasDoDesenho(true).altura);
  });
  it("abre no prédio mais perto de quem busca", () => {
    expect(predioInicial(["planalto", "governo", "prefeitura"])).toBe("prefeitura");
    expect(predioInicial(["planalto", "senado", "governo"])).toBe("governo");
  });
});
