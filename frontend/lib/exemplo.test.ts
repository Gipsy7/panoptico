import { describe, expect, it } from "vitest";

import { sortearCasa, sortearDupla, sortearItem } from "@/lib/exemplo";

const fixo = (...v: number[]) => {
  let i = 0;
  return () => v[i++ % v.length];
};

describe("sorteio do exemplo", () => {
  it("escolhe a casa pelo gerador", () => {
    expect(sortearCasa(() => 0.1)).toBe("senado");
    expect(sortearCasa(() => 0.9)).toBe("camara");
  });
  it("sorteia dois itens distintos", () => {
    expect(sortearDupla(["a", "b", "c"], fixo(0.0, 0.0))).toEqual(["a", "b"]);
    expect(sortearDupla(["a", "b", "c"], fixo(0.99, 0.99))).toEqual(["c", "b"]);
    expect(sortearDupla(["a", "b", "c"], fixo(0.5, 0.0))).toEqual(["b", "a"]);
  });
  it("sem itens suficientes não sorteia", () => {
    expect(sortearDupla(["a"])).toBeNull();
    expect(sortearItem([])).toBeUndefined();
    expect(sortearItem([1, 2, 3, 4], () => 0.999999)).toBe(4);
  });
});
