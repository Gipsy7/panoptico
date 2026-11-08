import { describe, expect, it } from "vitest";
import { formatarPct, larguraBarra, lugarDaDisputa, nomeCargo, nomeCargoPlural, situacaoSimples } from "./eleicao";

describe("eleicao", () => {
  it("nomes de cargo", () => {
    expect(nomeCargo("DEPUTADO FEDERAL")).toBe("Deputado federal");
    expect(nomeCargoPlural("DEPUTADO FEDERAL")).toBe("Deputados federais");
    expect(nomeCargoPlural("VEREADOR")).toBe("Vereadores");
    expect(nomeCargoPlural("GOVERNADOR")).toBe("Governadores");
  });

  it("situação do TSE em palavras simples", () => {
    expect(situacaoSimples("ELEITO POR QP")).toEqual({ texto: "Eleito", oficial: "pelo quociente partidário" });
    expect(situacaoSimples("NÃO ELEITO").texto).toBe("Não eleito");
    expect(situacaoSimples("2º TURNO").texto).toBe("Foi ao 2º turno");
    expect(situacaoSimples(null).texto).toBe("Sem resultado informado");
  });

  it("percentual e barra", () => {
    expect(formatarPct(51.4)).toBe("51,40%");
    expect(formatarPct(null)).toBe("—");
    expect(larguraBarra(50, 100)).toBe(50);
    expect(larguraBarra(0, 100)).toBe(0.5);
    expect(larguraBarra(1, 0)).toBe(0);
  });

  it("lugar da disputa", () => {
    expect(lugarDaDisputa({ uf: "BR", municipio: null })).toBe("Brasil");
    expect(lugarDaDisputa({ uf: null, municipio: { nome: "Blumenau", uf: "SC" } })).toBe("Blumenau (SC)");
  });
});
