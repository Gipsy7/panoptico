import { describe, expect, it } from "vitest";
import { paradasACada100 } from "./obras";

describe("obras", () => {
  it("paradas a cada 100 abertas", () => {
    const s = [
      { situacao: "Em execução", obras: 15 },
      { situacao: "Paralisada", obras: 3 },
      { situacao: "Inacabada", obras: 2 },
      { situacao: "Concluída", obras: 100 },
    ];
    expect(paradasACada100(s)).toBe(25);
  });
  it("sem obra aberta não tem conta", () => {
    expect(paradasACada100([{ situacao: "Concluída", obras: 4 }])).toBeNull();
    expect(paradasACada100([])).toBeNull();
  });
});
