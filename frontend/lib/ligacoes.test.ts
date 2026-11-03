import { describe, expect, it } from "vitest";

import { LIGACOES, VERBOS, chaveLigacao, ligacoesVisiveis, tracoLigacao } from "./ligacoes";

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
  it("toda ligação tem traço, com seta no fim", () => {
    for (const l of LIGACOES) {
      const t = tracoLigacao(l, 660);
      expect(t, chaveLigacao(l)).not.toBeNull();
      expect(t!.d).toMatch(/^M/);
      expect(t!.comprimento).toBeGreaterThan(20);
    }
  });
  it("a seta do Elege entra de lado, na altura da base do prédio", () => {
    const esq = tracoLigacao(LIGACOES.find((l) => l.para === "prefeitura" && l.verbo === "elege")!, 660)!;
    const dir = tracoLigacao(LIGACOES.find((l) => l.para === "camaramun" && l.verbo === "elege")!, 660)!;
    expect(esq.ang).toBe(0);
    expect(dir.ang).toBe(180);
    expect(esq.fim[1]).toBe(574);
  });
  it("o fio do Elege sai de Você, onde quer que o desenho termine", () => {
    const l = LIGACOES.find((x) => x.para === "governo" && x.verbo === "elege")!;
    expect(tracoLigacao(l, 466)!.d).toMatch(/^M180 446 /);
  });
  it("a ligação inversa (esquerda para direita) troca o sentido", () => {
    const a = tracoLigacao(LIGACOES.find((l) => l.de === "senado" && l.para === "planalto" && l.verbo === "julga")!, 660)!;
    const b = tracoLigacao(LIGACOES.find((l) => l.de === "planalto" && l.para === "senado")!, 660)!;
    expect(a.fim[0]).toBeLessThan(b.fim[0]);
  });
});
