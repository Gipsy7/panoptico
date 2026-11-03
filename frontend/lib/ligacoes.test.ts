import { describe, expect, it } from "vitest";

import { LIGACOES, VERBOS, caminhoCurvo, chaveLigacao, ligacoesVisiveis } from "./ligacoes";

const TODOS = ["planalto", "senado", "camara", "governo", "assembleia", "prefeitura", "camaramun"] as const;

describe("ligacoes", () => {
  it("o eleitor elege os sete prédios", () => {
    const elege = ligacoesVisiveis("elege", TODOS);
    expect(elege).toHaveLength(7);
    expect(elege.every((l) => l.de === "voce")).toBe(true);
  });
  it("sem filtro não há linhas", () => {
    expect(ligacoesVisiveis(null, TODOS)).toEqual([]);
  });
  it("some a ligação cujo prédio não existe (busca só por estado)", () => {
    const sem = TODOS.filter((id) => id !== "prefeitura" && id !== "camaramun");
    const todas = VERBOS.flatMap((v) => ligacoesVisiveis(v.id, sem));
    expect(todas.some((l) => l.de === "prefeitura" || l.para === "camaramun")).toBe(false);
    expect(ligacoesVisiveis("elege", sem)).toHaveLength(5);
  });
  it("toda ligação tem frase, artigo e chave única", () => {
    expect(new Set(LIGACOES.map(chaveLigacao)).size).toBe(LIGACOES.length);
    for (const l of LIGACOES) {
      expect(l.frase.length).toBeGreaterThan(10);
      expect(l.artigo).toMatch(/art/);
    }
  });
  it("ligações estaduais e municipais dizem de onde vem a regra", () => {
    const g = LIGACOES.find((l) => l.de === "governo" && l.verbo === "sanciona")!;
    expect(g.frase).toMatch(/constituição do estado/);
    const p = LIGACOES.find((l) => l.de === "prefeitura" && l.verbo === "sanciona")!;
    expect(p.artigo).toMatch(/lei orgânica/);
  });
  it("caminho curvo termina antes do destino", () => {
    const d = caminhoCurvo([0, 0], [100, 0], 1, 20);
    expect(d).toMatch(/^M0 0 Q/);
    const fim = Number(d.split(" ").at(-2));
    expect(fim).toBeLessThan(100);
  });
});
