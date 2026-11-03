import { describe, expect, it } from "vitest";

import {
  agrupar,
  cadeirasPorPartido,
  cadeirasPorVoto,
  descricaoCadeiras,
  descricaoVotos,
  layoutCadeiras,
  totalDe,
} from "@/lib/cadeiras";

describe("cadeiras", () => {
  it("agrupa somando, tirando zeros e ordenando por n e sigla", () => {
    const r = agrupar([
      { partido: "PT", n: 2 },
      { partido: "PL", n: 2 },
      { partido: "MDB", n: 0 },
      { partido: "PT", n: 1 },
    ]);
    expect(r).toEqual([
      { partido: "PT", n: 3 },
      { partido: "PL", n: 2 },
    ]);
    expect(totalDe(r)).toBe(5);
  });

  it("uma cadeira por parlamentar, partido a partido", () => {
    expect(cadeirasPorPartido([{ partido: "A", n: 2 }, { partido: "B", n: 1 }])).toEqual(["A", "A", "B"]);
    expect(cadeirasPorVoto(2, 1, 1)).toEqual(["sim", "sim", "nao", "outro"]);
  });

  it.each([1, 5, 81, 513])("o layout tem exatamente %i pontos dentro do desenho", (total) => {
    const { pontos, altura } = layoutCadeiras(total, 360);
    expect(pontos).toHaveLength(total);
    for (const p of pontos) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(360);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(altura);
    }
  });

  it("ordena da esquerda para a direita", () => {
    const { pontos } = layoutCadeiras(81);
    for (let i = 1; i < pontos.length; i++) expect(pontos[i].angulo).toBeLessThanOrEqual(pontos[i - 1].angulo);
  });

  it("sem cadeiras, sem pontos", () => {
    expect(layoutCadeiras(0).pontos).toEqual([]);
  });

  it("descreve com os números para leitor de tela", () => {
    const itens = [{ partido: "PL", n: 90 }, { partido: "PT", n: 68 }, { partido: "A", n: 1 }, { partido: "B", n: 1 }];
    expect(descricaoCadeiras("Câmara", itens, 2)).toBe("Câmara: 160 cadeiras. PL 90, PT 68 e mais 2 partidos.");
    expect(descricaoCadeiras("Câmara", [])).toBe("Câmara: sem dados de cadeiras.");
    expect(descricaoVotos("Votação", 300, 100, 113)).toContain("300 Sim, 100 Não e 113");
  });
});
