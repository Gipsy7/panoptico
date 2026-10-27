import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { acharCidade, lerAneis, pontoNoDesenho, projetar, type Malhas } from "@/lib/localizacao";

const lerJson = (p: string) =>
  JSON.parse(readFileSync(path.resolve(__dirname, "../public/mapa", p), "utf8"));
const malhas: Malhas = {
  ufs: async () => lerJson("ufs.json"),
  municipios: async (uf) => lerJson(`mun/${uf}.json`),
  detalhe: async (uf) => lerJson(`det/${uf}.json`),
};

describe("localizacao", () => {
  it("projeta como o script das malhas", () => {
    const [x, y] = projetar(5.35, -74.1);
    expect(x).toBeCloseTo(0);
    expect(y).toBeCloseTo(0);
  });

  it("lê M absoluto, l relativo e z", () => {
    expect(lerAneis("M0 0l10 0l0 10l-10 0z")).toEqual([
      [[0, 0], [10, 0], [10, 10], [0, 10]],
    ]);
  });

  it("trata buraco como fora", () => {
    const d = "M0 0l10 0l0 10l-10 0zM2 2l6 0l0 6l-6 0z";
    expect(pontoNoDesenho(1, 1, d)).toBe(true);
    expect(pontoNoDesenho(5, 5, d)).toBe(false);
    expect(pontoNoDesenho(20, 20, d)).toBe(false);
  });

  it.each([
    ["São Paulo", -23.5505, -46.6333, "SP", "São Paulo"],
    ["Gaspar", -26.9314, -48.9586, "SC", "Gaspar"],
    ["Palmas", -10.1844, -48.3336, "TO", "Palmas"],
    ["Manaus", -3.119, -60.0217, "AM", "Manaus"],
  ])("acha %s", async (_n, lat, lon, uf, nome) => {
    const c = await acharCidade(lat, lon, malhas);
    expect(c?.uf).toBe(uf);
    expect(c?.nome).toBe(nome);
  });

  it("fora do Brasil não acha cidade", async () => {
    expect(await acharCidade(48.85, 2.35, malhas)).toBeNull();
    expect(await acharCidade(-34.6, -58.38, malhas)).toBeNull();
  });
});
