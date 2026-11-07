import { describe, expect, it } from "vitest";

import type { CustoMandato, ItemCustoMandato } from "@/lib/api";
import { escalaDasBarras, listaNomes, periodoDoUso, segmentos } from "@/lib/custo-mandato";

const item = (parcial: Partial<ItemCustoMandato>): ItemCustoMandato => ({
  item: "subsidio",
  nome: "Salário",
  oficial: "Subsídio",
  valor: null,
  ato: null,
  ato_data: null,
  ato_url: null,
  valor_url: null,
  vigente_desde: null,
  consultado_em: "2026-11-07",
  observacao: null,
  usou: null,
  media_casa: null,
  usou_situacao: "fixo",
  usou_url: null,
  ...parcial,
});

describe("custo do mandato", () => {
  it("escreve o período do uso", () => {
    expect(periodoDoUso(2026, 10)).toBe("de janeiro a outubro de 2026");
    expect(periodoDoUso(2026, 1)).toBe("janeiro de 2026");
  });

  it("monta os pedaços da barra na escala comum e deixa de fora o que não tem número", () => {
    const itens = [
      item({ item: "subsidio", valor: 40, usou: 40 }),
      item({ item: "verba_gabinete", nome: "Verba", valor: null }),
      item({ item: "cota", nome: "Cota", valor: 60, usou: 10 }),
    ];
    expect(segmentos(itens, "valor", 100).map((s) => [s.item, s.largura])).toEqual([
      ["subsidio", 40],
      ["cota", 60],
    ]);
    expect(segmentos(itens, "usou", 100).map((s) => s.largura)).toEqual([40, 10]);
    expect(segmentos(itens, "valor", 0)).toEqual([]);
  });

  it("usa o maior total como escala", () => {
    const c = { total_se_usar_tudo: 100, usou_total: 120, media_total: 90 } as CustoMandato;
    expect(escalaDasBarras(c)).toBe(120);
  });

  it("junta nomes em português", () => {
    expect(listaNomes(["Salário"])).toBe("salário");
    expect(listaNomes(["Salário", "Gastos do gabinete"])).toBe("salário e gastos do gabinete");
    expect(listaNomes(["A", "B", "C"])).toBe("a, b e c");
    expect(listaNomes(["Moradia em Brasília"])).toBe("moradia em Brasília");
  });
});
