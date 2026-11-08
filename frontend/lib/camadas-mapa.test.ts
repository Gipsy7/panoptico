import { describe, expect, it } from "vitest";

import type { IndicadoresUfs } from "@/lib/api";
import { anoDaCamada, correlacao, frasePadrao, montarCamadas, ordenarDoMaior } from "@/lib/camadas-mapa";

const ind: IndicadoresUfs = {
  reais_de: 2025,
  indicadores: [
    {
      id: "homicidios",
      tema: "seguranca",
      grupo: "Segurança",
      rotulo: "Homicídios por 100 mil",
      titulo: "Homicídios por 100 mil moradores",
      unidade: "por 100 mil moradores",
      responsavel: "estado",
      decimais: 1,
      fonte_nome: "SIM",
      nota: null,
      anos: [2019, 2024],
      valores: { SC: [{ ano: 2019, valor: 10.7 }, { ano: 2024, valor: 8.1 }], RS: [{ ano: 2024, valor: 15 }] },
    },
  ],
};

describe("camadas do mapa", () => {
  const camadas = montarCamadas(
    [{ uf: "SC", nome: "Santa Catarina", arrecadacao: 100, repasse: 30 }],
    ind,
    2025,
    "Receita",
    null,
  );
  const hom = camadas.find((c) => c.id === "homicidios")!;

  it("lê o ano escolhido ou o último, e o dinheiro só no ano dele", () => {
    expect(hom.valor("SC")).toBe(8.1);
    expect(hom.valor("SC", 2019)).toBe(10.7);
    expect(hom.valor("RS", 2019)).toBeNull();
    const ret = camadas.find((c) => c.id === "retorno")!;
    expect(ret.valor("SC")).toBe(30);
    expect(ret.valor("SC", 2019)).toBeNull();
    expect(camadas.some((c) => c.id === "obras")).toBe(false);
  });

  it("ano da camada: o escolhido se ela tem, senão o último", () => {
    expect(anoDaCamada(hom, 2019)).toBe(2019);
    expect(anoDaCamada(hom, 2021)).toBe(2024);
  });

  it("correlação de postos e frase sem causa", () => {
    expect(correlacao([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])).toBeCloseTo(1);
    expect(correlacao([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])).toBeCloseTo(-1);
    expect(correlacao([1, 2, null, 4], [1, 2, 3, 4])).toBeNull();
    expect(frasePadrao(0.1)).toBe("sem padrão claro entre os estados");
    expect(frasePadrao(-0.7)).toBe("onde um é maior, o outro costuma ser menor");
  });

  it("ordena do maior para o menor, sem dado no fim", () => {
    const l = ordenarDoMaior([
      { nome: "Acre", valor: 3 },
      { nome: "Bahia", valor: null },
      { nome: "Ceará", valor: 9 },
      { nome: "Amapá", valor: 9 },
    ]);
    expect(l.map((x) => x.nome)).toEqual(["Amapá", "Ceará", "Acre", "Bahia"]);
  });
});
